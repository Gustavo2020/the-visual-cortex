"""
Unit tests for CLIP image search functionality.

Run with: pytest test_search.py -v
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from search import (
    CLIPSearchEngine, Config, SearchError,
    InvalidQueryError, InitializationError,
    search_images, get_engine
)


# ============================================================================
# Fixtures
# ============================================================================
@pytest.fixture
def temp_embeddings_dir():
    """Create temporary directory with mock embeddings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create mock embeddings
        embeddings = np.random.randn(10, 512).astype(np.float32)
        filenames = np.array([f"image_{i}.jpg" for i in range(10)])
        
        np.save(tmpdir_path / "image_embeddings.npy", embeddings)
        np.save(tmpdir_path / "image_filenames.npy", filenames)
        
        yield tmpdir_path


@pytest.fixture
def config_with_temp_dir(temp_embeddings_dir):
    """Create config pointing to temporary directory."""
    config = Config()
    config.EMBEDDINGS_DIR = temp_embeddings_dir
    return config


# ============================================================================
# Configuration Tests
# ============================================================================
class TestConfig:
    """Test configuration management."""
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = Config()
        assert config.MODEL_NAME == "ViT-B-32"
        assert config.PRETRAINED == "openai"
        assert config.DEVICE == "cpu"
        assert config.DEFAULT_TOP_K == 5
        assert config.MIN_QUERY_LENGTH == 2
    
    def test_config_env_override(self, monkeypatch):
        """Test environment variable overrides."""
        monkeypatch.setenv("CLIP_MODEL", "ViT-L-14")
        monkeypatch.setenv("CLIP_DEVICE", "cuda")
        monkeypatch.setenv("SEARCH_TOP_K", "10")
        
        config = Config()
        assert config.MODEL_NAME == "ViT-L-14"
        assert config.DEVICE == "cuda"
        assert config.DEFAULT_TOP_K == 10
    
    def test_validate_missing_directory(self, monkeypatch):
        """Test validation fails for missing directory."""
        monkeypatch.setenv("EMBEDDINGS_DIR", "/nonexistent/path")
        config = Config()
        assert not config.validate()
    
    def test_validate_missing_embeddings_file(self, temp_embeddings_dir):
        """Test validation fails for missing embeddings file."""
        embeddings_file = temp_embeddings_dir / "image_embeddings.npy"
        embeddings_file.unlink()
        
        config = Config()
        config.EMBEDDINGS_DIR = temp_embeddings_dir
        assert not config.validate()


# ============================================================================
# Exception Tests
# ============================================================================
class TestExceptions:
    """Test custom exceptions."""
    
    def test_search_error_inheritance(self):
        """Test SearchError is properly defined."""
        error = SearchError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"
    
    def test_invalid_query_error(self):
        """Test InvalidQueryError."""
        error = InvalidQueryError("query too short")
        assert isinstance(error, SearchError)
    
    def test_initialization_error(self):
        """Test InitializationError."""
        error = InitializationError("model loading failed")
        assert isinstance(error, SearchError)


# ============================================================================
# Engine Initialization Tests
# ============================================================================
class TestCLIPSearchEngineInit:
    """Test engine initialization."""
    
    def test_initialization_success(self, config_with_temp_dir):
        """Test successful engine initialization."""
        with patch("search.open_clip.create_model_and_transforms") as mock_create:
            # Mock CLIP model
            mock_model = Mock()
            mock_model.eval = Mock()
            mock_create.return_value = (mock_model, None, Mock())
            
            engine = CLIPSearchEngine(config=config_with_temp_dir)
            
            assert engine.image_embeddings is not None
            assert engine.image_filenames is not None
            assert engine.model is not None
    
    def test_initialization_missing_config(self):
        """Test initialization fails with invalid config."""
        config = Config()
        # Don't set valid embeddings dir
        
        with pytest.raises(InitializationError):
            CLIPSearchEngine(config=config)
    
    def test_initialization_shape_mismatch(self, temp_embeddings_dir):
        """Test initialization fails if embeddings shape doesn't match filenames."""
        # Create mismatched data
        embeddings = np.random.randn(10, 512).astype(np.float32)
        filenames = np.array([f"image_{i}.jpg" for i in range(5)])  # Only 5 filenames
        
        np.save(temp_embeddings_dir / "image_embeddings.npy", embeddings)
        np.save(temp_embeddings_dir / "image_filenames.npy", filenames)
        
        config = Config()
        config.EMBEDDINGS_DIR = temp_embeddings_dir
        
        with pytest.raises(InitializationError):
            CLIPSearchEngine(config=config)


# ============================================================================
# Query Validation Tests
# ============================================================================
class TestQueryValidation:
    """Test query validation."""
    
    @pytest.fixture
    def engine(self, config_with_temp_dir):
        """Create engine for validation tests."""
        with patch("search.open_clip.create_model_and_transforms") as mock_create:
            mock_model = Mock()
            mock_model.eval = Mock()
            mock_create.return_value = (mock_model, None, Mock())
            
            yield CLIPSearchEngine(config=config_with_temp_dir)
    
    def test_validate_query_not_string(self, engine):
        """Test validation fails for non-string query."""
        with pytest.raises(InvalidQueryError):
            engine._validate_query(123)
    
    def test_validate_query_too_short(self, engine):
        """Test validation fails for query too short."""
        with pytest.raises(InvalidQueryError):
            engine._validate_query("a")
    
    def test_validate_query_too_long(self, engine):
        """Test validation fails for query exceeding max length."""
        long_query = "a" * (engine.config.MAX_QUERY_LENGTH + 1)
        with pytest.raises(InvalidQueryError):
            engine._validate_query(long_query)
    
    def test_validate_query_whitespace_only(self, engine):
        """Test validation fails for whitespace-only query."""
        with pytest.raises(InvalidQueryError):
            engine._validate_query("   ")
    
    def test_validate_query_valid(self, engine):
        """Test validation succeeds for valid query."""
        # Should not raise
        engine._validate_query("a valid query")


# ============================================================================
# Search Functionality Tests
# ============================================================================
class TestSearchFunctionality:
    """Test search operations."""
    
    @pytest.fixture
    def engine(self, config_with_temp_dir):
        """Create engine for search tests."""
        with patch("search.open_clip.create_model_and_transforms") as mock_create:
            # Mock CLIP model with encode_text
            mock_model = Mock()
            mock_model.eval = Mock()
            
            # Mock text encoding to return normalized vectors
            mock_text_features = Mock()
            mock_text_features.cpu.return_value.numpy.return_value = np.array([[0.7, 0.7]])
            mock_text_features.norm.return_value = Mock()
            mock_text_features.norm.return_value.__truediv__ = Mock(
                return_value=mock_text_features
            )
            mock_model.encode_text = Mock(return_value=mock_text_features)
            
            mock_tokenizer = Mock()
            mock_create.return_value = (mock_model, None, mock_tokenizer)
            
            yield CLIPSearchEngine(config=config_with_temp_dir)
    
    def test_search_returns_results(self, engine):
        """Test search returns expected number of results."""
        with patch("search.open_clip.tokenize") as mock_tokenize:
            with patch.object(engine.model, 'encode_text') as mock_encode:
                # Create mock text features
                mock_features = np.ones((1, 512))
                mock_features = mock_features / np.linalg.norm(mock_features, axis=-1, keepdims=True)
                mock_encode.return_value = mock_features
                
                mock_tokenize.return_value = Mock()
                
                results = engine.search("test query", top_k=3)
                
                assert len(results) == 3
                assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
    
    def test_search_respects_top_k_limit(self, engine):
        """Test search respects top_k parameter."""
        with patch("search.open_clip.tokenize") as mock_tokenize:
            with patch.object(engine.model, 'encode_text') as mock_encode:
                mock_features = np.ones((1, 512))
                mock_features = mock_features / np.linalg.norm(mock_features, axis=-1, keepdims=True)
                mock_encode.return_value = mock_features
                
                mock_tokenize.return_value = Mock()
                
                # Request more results than available
                results = engine.search("test", top_k=20)
                
                # Should return at most the number of images in embeddings
                assert len(results) <= len(engine.image_filenames)
    
    def test_search_scores_in_valid_range(self, engine):
        """Test search scores are within valid range."""
        with patch("search.open_clip.tokenize") as mock_tokenize:
            with patch.object(engine.model, 'encode_text') as mock_encode:
                mock_features = np.ones((1, 512))
                mock_features = mock_features / np.linalg.norm(mock_features, axis=-1, keepdims=True)
                mock_encode.return_value = mock_features
                
                mock_tokenize.return_value = Mock()
                
                results = engine.search("test", top_k=5)
                
                for _, score in results:
                    assert -1.0 <= score <= 1.0


# ============================================================================
# Context Manager Tests
# ============================================================================
class TestContextManager:
    """Test context manager functionality."""
    
    def test_context_manager_cleanup(self, config_with_temp_dir):
        """Test context manager properly cleans up."""
        with patch("search.open_clip.create_model_and_transforms") as mock_create:
            mock_model = Mock()
            mock_model.eval = Mock()
            mock_create.return_value = (mock_model, None, Mock())
            
            with CLIPSearchEngine(config=config_with_temp_dir) as engine:
                assert engine.model is not None
            
            # After context, model should be cleaned up
            assert engine.model is None


# ============================================================================
# Public API Tests
# ============================================================================
class TestPublicAPI:
    """Test public API functions."""
    
    def test_search_images_function(self, monkeypatch, config_with_temp_dir, temp_embeddings_dir):
        """Test public search_images function."""
        monkeypatch.setenv("EMBEDDINGS_DIR", str(temp_embeddings_dir))
        
        with patch("search.open_clip.create_model_and_transforms") as mock_create:
            mock_model = Mock()
            mock_model.eval = Mock()
            mock_create.return_value = (mock_model, None, Mock())
            
            # Reset global engine
            import search
            search._engine = None
            
            with patch("search.open_clip.tokenize") as mock_tokenize:
                with patch("search.CLIPSearchEngine.search") as mock_search:
                    mock_search.return_value = [("image.jpg", 0.85)]
                    
                    results = search_images("test query")
                    
                    assert len(results) > 0
    
    def test_get_engine_singleton(self):
        """Test get_engine returns singleton instance."""
        import search
        search._engine = None  # Reset
        
        with patch.object(CLIPSearchEngine, '__init__', return_value=None):
            engine1 = get_engine()
            engine2 = get_engine()
            
            assert engine1 is engine2


# ============================================================================
# Integration Tests
# ============================================================================
class TestIntegration:
    """Integration tests."""
    
    def test_full_search_workflow(self, config_with_temp_dir):
        """Test complete search workflow."""
        with patch("search.open_clip.create_model_and_transforms") as mock_create:
            mock_model = Mock()
            mock_model.eval = Mock()
            
            # Create proper mock for text encoding
            mock_features = np.ones((1, 512), dtype=np.float32)
            mock_features = mock_features / np.linalg.norm(mock_features)
            mock_model.encode_text = Mock(return_value=mock_features)
            
            mock_create.return_value = (mock_model, None, Mock())
            
            with patch("search.open_clip.tokenize") as mock_tokenize:
                mock_tokenize.return_value = Mock()
                
                engine = CLIPSearchEngine(config=config_with_temp_dir)
                results = engine.search("test query", top_k=5)
                
                assert isinstance(results, list)
                assert all(isinstance(r[0], str) for r in results)
                assert all(isinstance(r[1], float) for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
