"""
CLIP/SigLIP image embedding pipeline (CPU-only by default).

- Loads images from data/images
- Generates CLIP embeddings
- Benchmarks CPU time and memory usage
- Saves embeddings and metadata to disk
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Any

import numpy as np
import psutil
import torch
from PIL import Image
from tqdm import tqdm
import open_clip


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Configuration (model/pretrained can be any CLIP or SigLIP variant supported by open_clip)
# ====================================
BASE_DIR = Path(__file__).parent.parent
IMAGE_DIR = BASE_DIR / "data" / "images"
OUTPUT_DIR = BASE_DIR / "data" / "embeddings"
MODEL_NAME = os.getenv("CLIP_MODEL", "ViT-B-32")  # ViT-B-32, ViT-B-16, ViT-L-14
PRETRAINED = os.getenv("CLIP_PRETRAINED", "openai")
DEVICE = os.getenv("CLIP_DEVICE", "cpu")

# Validate and create directories
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Image directory: {IMAGE_DIR}")
logger.info(f"Output directory: {OUTPUT_DIR}")


# Load CLIP model
# ====================================
logger.info("Loading CLIP model on CPU...")
try:
    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME,
        pretrained=PRETRAINED,
        device=DEVICE
    )
    model.eval()
    # preprocess is a torchvision Transform (callable)
    preprocess: Any = preprocess  # type: ignore
    logger.info(f"Model loaded successfully: {MODEL_NAME} ({PRETRAINED})")
except Exception as e:
    logger.error(f"Failed to load model: {e}")
    raise


# Prepare image list
# ====================================
image_paths = sorted(IMAGE_DIR.glob("*.jpg")) + sorted(IMAGE_DIR.glob("*.png"))

if len(image_paths) == 0:
    logger.error(f"No images found in {IMAGE_DIR}")
    raise FileNotFoundError(f"No images (.jpg, .png) found in {IMAGE_DIR}")

logger.info(f"Found {len(image_paths)} images to process")


# Embedding loop
# ====================================
embeddings = []
filenames = []
failed_images = []

process = psutil.Process()
start_mem = process.memory_info().rss / 1e6
start_time = time.time()

with torch.no_grad():
    for img_path in tqdm(image_paths, desc="Embedding images"):
        try:
            # Load and preprocess image
            image = Image.open(img_path).convert("RGB")
            image_tensor = preprocess(image).unsqueeze(0).to(DEVICE)

            # Generate embedding
            image_features = model.encode_image(image_tensor)  # type: ignore
            # L2 normalization
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            embeddings.append(image_features.cpu().numpy()[0])
            filenames.append(img_path.name)
        except Exception as e:
            logger.warning(f"Failed to process {img_path.name}: {e}")
            failed_images.append(str(img_path.name))

end_time = time.time()


# Save results
# ====================================
if len(embeddings) == 0:
    logger.error("No embeddings generated!")
    raise ValueError("No valid images were processed")

embeddings = np.vstack(embeddings)

# Save embeddings and metadata
embeddings_path = OUTPUT_DIR / "image_embeddings.npy"
filenames_path = OUTPUT_DIR / "image_filenames.npy"
metadata_path = OUTPUT_DIR / "metadata.json"

np.save(embeddings_path, embeddings)
np.save(filenames_path, np.array(filenames))
logger.info(f"Embeddings saved to {embeddings_path}")
logger.info(f"Filenames saved to {filenames_path}")

# Save metadata
elapsed = end_time - start_time
end_mem = process.memory_info().rss / 1e6
memory_used = end_mem - start_mem

metadata = {
    "timestamp": datetime.now().isoformat(),
    "model": MODEL_NAME,
    "pretrained": PRETRAINED,
    "device": DEVICE,
    "images_processed": len(filenames),
    "images_failed": len(failed_images),
    "failed_images": failed_images,
    "embedding_dimension": int(embeddings.shape[1]),
    "total_time_seconds": round(elapsed, 2),
    "avg_time_per_image_seconds": round(elapsed / len(filenames), 4),
    "memory_used_mb": round(memory_used, 1),
}

with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=2)
logger.info(f"Metadata saved to {metadata_path}")

# Print summary
# ====================================
print("\n" + "="*50)
print("     CPU EMBEDDING SUMMARY")
print("="*50)
print(f"Images processed     : {len(filenames)}")
print(f"Images failed        : {len(failed_images)}")
print(f"Embedding dimension  : {embeddings.shape[1]}")
print(f"Total time (sec)     : {elapsed:.2f}")
print(f"Avg time / image (s) : {elapsed / len(filenames):.4f}")
print(f"Memory used (MB)     : {memory_used:.1f}")
print("="*50)
