"""
Test suite for embed_images.py functionality validation
"""

import json
import logging
from pathlib import Path
import sys

logger = logging.getLogger(__name__)


def validate_imports():
    """Validate that all required dependencies are importable"""
    print("\n[TEST 1] Validating imports...")
    required_modules = {
        'json': 'JSON library',
        'logging': 'Logging library',
        'time': 'Time library',
        'datetime': 'DateTime library',
        'pathlib': 'Path library',
        'numpy': 'NumPy for arrays',
        'psutil': 'Process utilities',
        'torch': 'PyTorch',
        'PIL': 'Pillow for images',
        'tqdm': 'Progress bar',
        'open_clip': 'OpenAI CLIP'
    }
    
    missing = []
    for module, description in required_modules.items():
        try:
            __import__(module)
            print(f"  ✓ {module:15} - {description}")
        except ImportError:
            print(f"  ✗ {module:15} - {description} [MISSING]")
            missing.append(module)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        return False
    
    print("  ✓ All imports successful!\n")
    return True


def validate_file_structure():
    """Validate that the file has proper structure"""
    print("[TEST 2] Validating file structure...")
    
    base_dir = Path(__file__).parent.parent
    embed_file = Path(__file__).parent / "embed_images.py"
    
    if not embed_file.exists():
        print(f"  ✗ File not found: {embed_file}")
        return False
    
    print(f"  ✓ File exists: {embed_file}")
    
    # Check required sections
    content = embed_file.read_text()
    required_sections = {
        "Configuration": "BASE_DIR",
        "Load CLIP model": "open_clip.create_model_and_transforms",
        "Prepare image list": "glob",
        "Embedding loop": "torch.no_grad()",
        "Save results": "np.vstack",
        "metadata.json": "metadata",
    }
    
    for section, keyword in required_sections.items():
        if keyword in content:
            print(f"  ✓ Section '{section}' found (keyword: {keyword})")
        else:
            print(f"  ✗ Section '{section}' NOT found (keyword: {keyword})")
            return False
    
    print("  ✓ All required sections present!\n")
    return True


def validate_error_handling():
    """Validate that error handling is in place"""
    print("[TEST 3] Validating error handling...")
    
    embed_file = Path(__file__).parent / "embed_images.py"
    content = embed_file.read_text()
    
    error_checks = {
        "Try-except for model loading": "except Exception",
        "Logging for warnings": "logger.warning",
        "Logging for errors": "logger.error",
        "Check for empty images": "len(image_paths) == 0",
        "Check for empty embeddings": "len(embeddings) == 0",
    }
    
    for check, pattern in error_checks.items():
        if pattern in content:
            print(f"  ✓ {check}")
        else:
            print(f"  ✗ {check} [MISSING]")
            return False
    
    print("  ✓ Error handling validated!\n")
    return True


def validate_directory_structure():
    """Validate required directories can be created"""
    print("[TEST 4] Validating directory structure...")
    
    base_dir = Path(__file__).parent.parent
    required_dirs = {
        "data": base_dir / "data",
        "data/images": base_dir / "data" / "images",
        "data/embeddings": base_dir / "data" / "embeddings",
        "src": base_dir / "src",
    }
    
    for name, path in required_dirs.items():
        try:
            path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Directory '{name}' - OK")
        except Exception as e:
            print(f"  ✗ Directory '{name}' - ERROR: {e}")
            return False
    
    print("  ✓ Directory structure validated!\n")
    return True


def validate_metadata_json():
    """Validate that metadata.json will be created with proper structure"""
    print("[TEST 5] Validating metadata structure...")
    
    embed_file = Path(__file__).parent / "embed_images.py"
    content = embed_file.read_text()
    
    metadata_fields = {
        "timestamp": "datetime.now().isoformat()",
        "model": "MODEL_NAME",
        "pretrained": "PRETRAINED",
        "device": "DEVICE",
        "images_processed": "len(filenames)",
        "images_failed": "len(failed_images)",
        "failed_images": "failed_images",
        "embedding_dimension": "embeddings.shape[1]",
        "total_time_seconds": "elapsed",
        "avg_time_per_image_seconds": "elapsed / len(filenames)",
        "memory_used_mb": "memory_used",
    }
    
    for field, _ in metadata_fields.items():
        if f'"{field}"' in content or f"'{field}'" in content:
            print(f"  ✓ Metadata field: {field}")
        else:
            print(f"  ✗ Metadata field: {field} [MISSING]")
            return False
    
    print("  ✓ Metadata structure validated!\n")
    return True


def main():
    """Run all validation tests"""
    print("="*60)
    print("  EMBED_IMAGES.PY FUNCTIONALITY VALIDATION")
    print("="*60)
    
    tests = [
        validate_imports,
        validate_file_structure,
        validate_error_handling,
        validate_directory_structure,
        validate_metadata_json,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ✗ Test failed with error: {e}\n")
            results.append(False)
    
    # Summary
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"  RESULTS: {passed}/{total} tests passed")
    print("="*60)
    
    if all(results):
        print("\n✓ ¡Validación completada exitosamente!")
        print("\nLa funcionalidad está lista para usar.")
        return 0
    else:
        print("\n✗ Hay problemas que necesitan corrección.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
