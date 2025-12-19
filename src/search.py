"""
Production-ready semantic text-to-image search using CLIP embeddings.

This module provides a robust image search interface with:
- Error handling and validation
- Structured logging
- Type hints
- Configuration management
- Resource cleanup via context managers
"""

import logging
import os
from pathlib import Path
from typing import List, Tuple, Optional, Any
from contextlib import contextmanager

import numpy as np
import torch
import open_clip
import tempfile
from PIL import Image, ImageDraw
import torch.nn.functional as F


# ============================================================================
# Configuration Management
# ============================================================================
logger = logging.getLogger(__name__)

# Base directory of the repository (one level above src)
BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Centralized configuration for search service."""
    
    # Default to repository-level data/embeddings, override via EMBEDDINGS_DIR
    DEFAULT_EMBEDDINGS_DIR: Path = BASE_DIR / "data" / "embeddings"
    EMBEDDINGS_DIR: Path = Path(
        os.getenv("EMBEDDINGS_DIR", str(DEFAULT_EMBEDDINGS_DIR))
    )
    MODEL_NAME: str = os.getenv("CLIP_MODEL", "ViT-B-32")
    PRETRAINED: str = os.getenv("CLIP_PRETRAINED", "openai")
    TOKENIZER_NAME: Optional[str] = os.getenv("CLIP_TOKENIZER")
    DEVICE: str = os.getenv("CLIP_DEVICE", "cpu")
    DTYPE: str = os.getenv("CLIP_DTYPE", "auto")  # auto, float32, float16
    NORMALIZE_EMBEDDINGS: bool = os.getenv("NORMALIZE_EMBEDDINGS", "1").lower() in ("1", "true", "yes")
    DEFAULT_TOP_K: int = int(os.getenv("SEARCH_TOP_K", "5"))
    MIN_QUERY_LENGTH: int = 2
    MAX_QUERY_LENGTH: int = 512
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration paths and settings."""
        if not cls.EMBEDDINGS_DIR.exists():
            logger.error(f"Embeddings directory not found: {cls.EMBEDDINGS_DIR}")
            return False
        
        embeddings_file = cls.EMBEDDINGS_DIR / "image_embeddings.npy"
        filenames_file = cls.EMBEDDINGS_DIR / "image_filenames.npy"
        
        if not embeddings_file.exists():
            logger.error(f"Embeddings file not found: {embeddings_file}")
            return False
        
        if not filenames_file.exists():
            logger.error(f"Filenames file not found: {filenames_file}")
            return False
        
        return True


# ============================================================================
# Custom Exceptions
# ============================================================================
class SearchError(Exception):
    """Base exception for search operations."""
    pass


class InitializationError(SearchError):
    """Raised when search service fails to initialize."""
    pass


class InvalidQueryError(SearchError):
    """Raised when query validation fails."""
    pass


# ============================================================================
# CLIP Search Engine
# ============================================================================
class CLIPSearchEngine:
    """
    Semantic image search using CLIP embeddings.
    
    This class manages CLIP model lifecycle and provides efficient
    similarity search over pre-computed image embeddings.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the search engine.
        
        Args:
            config: Configuration object. Defaults to Config class.
            
        Raises:
            InitializationError: If model or embeddings cannot be loaded.
        """
        self.config = config or Config()
        self.model: Any = None  # Will be set in _initialize()
        self.tokenizer: Any = None  # Will be set in _initialize()
        self.image_embeddings: Any = None  # Numpy array
        self.image_filenames: Any = None  # Numpy array
        self.image_embeddings_t: Any = None  # Torch tensor on device
        self.device = torch.device(self.config.DEVICE)
        
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize model and load embeddings."""
        logger.info("Initializing CLIP Search Engine...")
        
        # Validate configuration
        if not self.config.validate():
            raise InitializationError("Configuration validation failed")
        
        try:
            # Load embeddings
            logger.info(f"Loading embeddings from {self.config.EMBEDDINGS_DIR}")
            embeddings_file = self.config.EMBEDDINGS_DIR / "image_embeddings.npy"
            filenames_file = self.config.EMBEDDINGS_DIR / "image_filenames.npy"
            
            # Use memory map to keep memory footprint low on large arrays
            try:
                self.image_embeddings = np.load(embeddings_file, mmap_mode="r")
            except TypeError:
                self.image_embeddings = np.load(embeddings_file)
            self.image_filenames = np.load(filenames_file, allow_pickle=True)
            
            # Validate embeddings consistency
            if self.image_embeddings.shape[0] != len(self.image_filenames):
                raise InitializationError(
                    f"Embeddings shape {self.image_embeddings.shape[0]} "
                    f"does not match filenames length {len(self.image_filenames)}"
                )
            
            logger.info(
                f"Loaded {len(self.image_filenames)} image embeddings "
                f"with shape {self.image_embeddings.shape}"
            )
            
            # Load CLIP model
            logger.info(
                f"Loading CLIP/SigLIP model: {self.config.MODEL_NAME} "
                f"(pretrained={self.config.PRETRAINED})"
            )
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                self.config.MODEL_NAME,
                pretrained=self.config.PRETRAINED,
                device=self.config.DEVICE
            )
            self.model.eval()

            tokenizer_name = self.config.TOKENIZER_NAME or self.config.MODEL_NAME
            try:
                self.tokenizer = open_clip.get_tokenizer(tokenizer_name)
                logger.info(f"Tokenizer initialized for model: {tokenizer_name}")
            except Exception as e:
                logger.warning(
                    "Tokenizer fallback to default CLIP tokenizer for %s due to: %s",
                    tokenizer_name,
                    str(e)
                )
                self.tokenizer = open_clip.tokenize  # type: ignore

            # Prepare embeddings tensor on device for fast cosine similarity
            emb_np = np.ascontiguousarray(self.image_embeddings.astype(np.float32))
            emb_t = torch.from_numpy(emb_np)
            # Move to device with appropriate dtype
            if self.config.DTYPE == "float16" or (self.config.DTYPE == "auto" and self.device.type == "cuda"):
                emb_t = emb_t.to(self.device, dtype=torch.float16)
            else:
                emb_t = emb_t.to(self.device, dtype=torch.float32)
            # Normalize rows if configured
            if self.config.NORMALIZE_EMBEDDINGS:
                emb_t = F.normalize(emb_t, p=2, dim=1)
            self.image_embeddings_t = emb_t
            
            logger.info("CLIP Search Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize search engine: {str(e)}")
            raise InitializationError(f"Initialization failed: {str(e)}") from e
    
    def _validate_query(self, query: str) -> None:
        """
        Validate query input.
        
        Args:
            query: Text query to validate.
            
        Raises:
            InvalidQueryError: If query is invalid.
        """
        if not isinstance(query, str):
            raise InvalidQueryError("Query must be a string")
        
        query_stripped = query.strip()
        
        if len(query_stripped) < self.config.MIN_QUERY_LENGTH:
            raise InvalidQueryError(
                f"Query too short (minimum {self.config.MIN_QUERY_LENGTH} characters)"
            )
        
        if len(query_stripped) > self.config.MAX_QUERY_LENGTH:
            raise InvalidQueryError(
                f"Query too long (maximum {self.config.MAX_QUERY_LENGTH} characters)"
            )
    
    def search(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[Tuple[str, float]]:
        """
        Perform semantic search over image embeddings.
        
        Args:
            query: Text query for image search.
            top_k: Number of results to return. Defaults to config.DEFAULT_TOP_K.
            
        Returns:
            List of (filename, similarity_score) tuples sorted by score descending.
            
        Raises:
            InvalidQueryError: If query validation fails.
            SearchError: If search operation fails.
        """
        if top_k is None:
            top_k = self.config.DEFAULT_TOP_K
        
        # Validate inputs
        self._validate_query(query)
        
        if not isinstance(top_k, int) or top_k < 1:
            raise InvalidQueryError("top_k must be a positive integer")
        
        top_k = min(top_k, self.num_images)
        
        try:
            logger.debug(f"Searching for: '{query}' (top_k={top_k})")
            
            with torch.no_grad():
                # Tokenize and encode query (supports CLIP and SigLIP tokenizers)
                tokenize_fn = self.tokenizer or open_clip.tokenize
                text_tokens = tokenize_fn([query])
                if not isinstance(text_tokens, torch.Tensor):
                    text_tokens = torch.as_tensor(text_tokens)
                text_tokens = text_tokens.to(self.device)

                text_features = self.model.encode_text(text_tokens)
                # Cast to match embeddings dtype and normalize
                if self.image_embeddings_t.dtype == torch.float16:
                    text_features = text_features.to(self.device, dtype=torch.float16)
                else:
                    text_features = text_features.to(self.device, dtype=torch.float32)
                text_features = F.normalize(text_features, p=2, dim=-1)

                # Compute cosine similarities via matmul on device
                # text_features[0] is 1D [D], no transpose needed
                similarities = self.image_embeddings_t @ text_features[0]  # [N]
                scores, idx = torch.topk(similarities, k=top_k, largest=True)
                idx_list = idx.detach().cpu().tolist()
                scores_list = scores.detach().cpu().tolist()

            # Build results on CPU
            results = [
                (str(self.image_filenames[i]), float(s))
                for i, s in zip(idx_list, scores_list)
            ]
            
            logger.info(f"Search completed for '{query}': found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise SearchError(f"Search operation failed: {str(e)}") from e
    
    @property
    def num_images(self) -> int:
        """Return the number of indexed images."""
        if self.image_filenames is None:
            return 0
        return len(self.image_filenames)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up CLIP Search Engine resources")
        if self.model is not None:
            del self.model
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


# ============================================================================
# Global Engine Instance (Lazy Loading)
# ============================================================================
_engine: Optional[CLIPSearchEngine] = None


def get_engine() -> CLIPSearchEngine:
    """Get or create the global search engine instance."""
    global _engine
    if _engine is None:
        logger.info("Creating global search engine instance")
        _engine = CLIPSearchEngine()
    return _engine


# ============================================================================
# Public API
# ============================================================================
def search_images(
    query: str,
    top_k: Optional[int] = None
) -> List[Tuple[str, float]]:
        # Type narrowing: assertions above guarantee image_filenames is not None
    """
    Perform semantic search over image embeddings.
    
    This is the main entry point for searching images by text query.
    
    Args:
        query: Text query describing desired images.
        top_k: Number of results to return. Defaults to configuration value.
        
    Returns:
        List of (filename, similarity_score) tuples, sorted by score descending.
        Scores range from -1 to 1 (cosine similarity).
        
    Raises:
        InvalidQueryError: If query is invalid.
        SearchError: If search operation fails.
        
    Example:
        >>> results = search_images("a red car")
        >>> for filename, score in results:
        ...     print(f"{filename}: {score:.4f}")
    """
    engine = get_engine()
    return engine.search(query, top_k)


# ============================================================================
# CLI Interface (Development/Testing)
# ============================================================================
def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for command-line usage."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def interactive_search() -> None:
    """Interactive command-line search interface with preview options."""
    def _resolve_image_path(filename: str) -> Path:
        return BASE_DIR / "data" / "images" / filename

    def _open_image(filename: str) -> None:
        path = _resolve_image_path(filename)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        # Copy to output location with readable name
        output_path = BASE_DIR / f"result_{filename}"
        from shutil import copy2
        copy2(path, output_path)
        print(f"\nImage saved to: {output_path}")
        print(f"Download via: scp user@host:{output_path} .")
        print(f"Or use REST API: python3 src/api.py (then /docs for Swagger UI)\n")

    def _preview_grid(results: List[Tuple[str, float]], cols: int = 3, thumb: int = 256) -> None:
        sel = results[: max(1, min(len(results), cols * 2))]
        if not sel:
            return
        images = []
        labels = []
        for fname, score in sel:
            p = _resolve_image_path(fname)
            if not p.exists():
                continue
            try:
                im = Image.open(p).convert("RGB")
                im.thumbnail((thumb, thumb))
                images.append(im)
                labels.append(f"{fname} | {score:.3f}")
            except Exception:
                continue
        if not images:
            raise RuntimeError("No previewable images found")
        rows = (len(images) + cols - 1) // cols
        w = cols * thumb
        h = rows * (thumb + 24)
        grid = Image.new("RGB", (w, h), (20, 20, 20))
        draw = ImageDraw.Draw(grid)
        for idx, im in enumerate(images):
            r = idx // cols
            c = idx % cols
            x = c * thumb
            y = r * (thumb + 24)
            grid.paste(im, (x, y))
            lbl = labels[idx]
            draw.rectangle((x, y + thumb, x + thumb, y + thumb + 24), fill=(0, 0, 0))
            draw.text((x + 4, y + thumb + 4), lbl[:40], fill=(255, 255, 255))
        out = BASE_DIR / "preview_grid.jpg"
        grid.save(out)
        print(f"\nPreview grid saved to: {out}")
        print(f"Download via: scp user@host:{out} .")
        print(f"Or use REST API: python3 src/api.py (then /docs for Swagger UI)\n")

    print("\n" + "=" * 70)
    print("CLIP Semantic Image Search")
    print("=" * 70)
    print("Enter text queries to search for similar images.")
    print("Type 'exit' or 'quit' to exit.\n")

    try:
        while True:
            try:
                query = input("Enter search query: ").strip()

                if query.lower() in ('exit', 'quit'):
                    print("Goodbye!")
                    break

                if not query:
                    print("Warning: Query cannot be empty\n")
                    continue

                results = search_images(query, top_k=5)

                print(f"\nTop {len(results)} matches for '{query}':")
                print("-" * 70)
                for i, (filename, score) in enumerate(results, 1):
                    print(f"  {i}. {filename:40} | Similarity: {score:.4f}")
                print()

                choice = input("Preview: [p]=grid, [1-9]=open index, [Enter]=skip: ").strip().lower()
                if choice == 'p' and results:
                    try:
                        _preview_grid(results)
                    except Exception as e:
                        print(f"Preview failed: {e}")
                elif choice.isdigit():
                    idx = int(choice)
                    if 1 <= idx <= len(results):
                        try:
                            _open_image(results[idx-1][0])
                        except Exception as e:
                            print(f"Open failed: {e}")

            except InvalidQueryError as e:
                print(f"Error: {str(e)}\n")
            except SearchError as e:
                print(f"Search error: {str(e)}\n")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
    except Exception as e:
        logger.exception("Unexpected error during interactive search")
        print(f"Fatal error: {str(e)}")


if __name__ == "__main__":
    import sys
    setup_logging(level=logging.INFO)

    def sanity_check() -> int:
        """Quick validation of embeddings presence and shape without loading the model."""
        try:
            cfg = Config()
            base = cfg.EMBEDDINGS_DIR
            emb_file = base / "image_embeddings.npy"
            fn_file = base / "image_filenames.npy"

            print("\nEmbeddings sanity check")
            print("-" * 40)
            print(f"Embeddings dir : {base}")
            print(f"Embeddings file: {emb_file} ({'exists' if emb_file.exists() else 'missing'})")
            print(f"Filenames file : {fn_file} ({'exists' if fn_file.exists() else 'missing'})")

            if not emb_file.exists() or not fn_file.exists():
                print("Result         : MISSING files. Run embed_images.py first.")
                return 1

            emb = np.load(emb_file, mmap_mode="r")
            fns = np.load(fn_file, allow_pickle=True)
            n, d = emb.shape[0], emb.shape[1]
            print(f"Embeddings     : shape=({n}, {d}), dtype={emb.dtype}")
            print(f"Filenames      : count={len(fns)}")
            ok = n == len(fns)
            print(f"Consistency    : {'OK' if ok else 'MISMATCH'}")
            return 0 if ok else 2
        except Exception as e:
            print(f"Check failed    : {e}")
            return 3

    if len(sys.argv) > 1:
        if "--check" in sys.argv:
            raise SystemExit(sanity_check())
        if "--check-engine" in sys.argv:
            try:
                eng = get_engine()
                print("\nEngine check")
                print("-" * 40)
                print(f"Model      : {eng.config.MODEL_NAME}")
                print(f"Device     : {eng.config.DEVICE}")
                print(f"Num images : {eng.num_images}")
                raise SystemExit(0)
            except Exception as e:
                print(f"Engine init failed: {e}")
                raise SystemExit(1)

    interactive_search()
