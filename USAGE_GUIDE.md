# Usage Guide: embed_images.py

## Overview

`embed_images.py` is a pipeline that generates image embeddings using the OpenAI CLIP model. It is optimized for CPU execution and reports detailed performance metrics.

### What it does

1. Loads images from `data/images/` (.jpg and .png)
2. Generates embeddings with CLIP ViT-B-32
3. Saves outputs to `data/embeddings/`:
   - `image_embeddings.npy` - Embedding matrix (N x 512)
   - `image_filenames.npy` - Image filenames
   - `metadata.json` - Execution metadata
4. Records time and memory metrics

---

## Quick Setup

### Step 1: Move to project root

```bash
cd /home/arcanegus/the-visual-cortex
```

### Step 2: Create a virtual environment (recommended)

```bash
# Using venv
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or with conda
conda create -n visual-cortex python=3.10
conda activate visual-cortex
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

Note: PyTorch is large. If you have an NVIDIA GPU, consider the CUDA wheel:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## Directory Layout

```
the-visual-cortex/
├── src/
│   ├── embed_images.py          # Main script
│   ├── test_embed_images.py     # Validation suite
│   ├── embed.py                 # Placeholder for future use
│   ├── search.py                # Placeholder for search
│   ├── ingest.py                # Placeholder for ingest
│   ├── config.py                # Placeholder for config
│   └── utils.py                 # Placeholder for utilities
├── data/
│   ├── images/                  # Place your input images here
│   └── embeddings/              # Generated embeddings
├── requirements.txt             # Dependencies
├── VALIDATION_REPORT.md         # Validation report
└── USAGE_GUIDE.md               # This guide
```

---

## Prepare Images

### 1) Create the image folder

```bash
mkdir -p data/images
```

### 2) Add images

```bash
# Copy individual files
cp /path/to/image1.jpg data/images/
cp /path/to/image2.png data/images/

# Or copy an entire folder
cp -r /path/to/my_images/* data/images/
```

### Supported formats
- JPEG (.jpg, .jpeg)
- PNG (.png)

### Example preparation

```bash
# Download sample images
cd data/images
wget https://example.com/image1.jpg
wget https://example.com/image2.jpg
wget https://example.com/image3.jpg
cd ../../
```

---

## Run the Script

### Basic run

```bash
python src/embed_images.py
```

### Verbose output

```bash
python -u src/embed_images.py 2>&1 | tee embeddings.log
```

### Expected output (example)

```
2025-12-17 14:30:25,123 - INFO - Image directory: .../data/images
2025-12-17 14:30:25,124 - INFO - Output directory: .../data/embeddings
2025-12-17 14:30:26,456 - INFO - Loading CLIP model on CPU...
2025-12-17 14:30:45,789 - INFO - Model loaded successfully: ViT-B-32 (openai)
2025-12-17 14:30:45,790 - INFO - Found 10 images to process

Embedding images: 100%|████████████| 10/10 [00:35<00:00,  3.50s/it]

2025-12-17 14:31:21,234 - INFO - Embeddings saved to .../data/embeddings/image_embeddings.npy
2025-12-17 14:31:21,235 - INFO - Filenames saved to .../data/embeddings/image_filenames.npy
2025-12-17 14:31:21,236 - INFO - Metadata saved to .../data/embeddings/metadata.json

==================================================
     CPU EMBEDDING SUMMARY
==================================================
Images processed     : 10
Images failed        : 0
Embedding dimension  : 512
Total time (sec)     : 35.12
Avg time / image (s) : 3.5120
Memory used (MB)     : 185.4
==================================================
```

---

## Interpret Results

### Generated files

#### 1) `image_embeddings.npy`
```python
import numpy as np

embeddings = np.load('data/embeddings/image_embeddings.npy')
print(embeddings.shape)  # (N, 512)
print(embeddings[0])
```

#### 2) `image_filenames.npy`
```python
import numpy as np

filenames = np.load('data/embeddings/image_filenames.npy')
print(filenames)
print(filenames[0])
```

#### 3) `metadata.json`
```python
import json

with open('data/embeddings/metadata.json') as f:
    metadata = json.load(f)

print(metadata)
# {
#     "timestamp": "2025-12-17T14:31:21.236123",
#     "model": "ViT-B-32",
#     "pretrained": "openai",
#     "device": "cpu",
#     "images_processed": 10,
#     "images_failed": 0,
#     "failed_images": [],
#     "embedding_dimension": 512,
#     "total_time_seconds": 35.12,
#     "avg_time_per_image_seconds": 3.512,
#     "memory_used_mb": 185.4
# }
```

---

## Validation Tests

### Run the suite

```bash
python src/test_embed_images.py
```

### Expected output

```
==========================================================
  EMBED_IMAGES.PY FUNCTIONALITY VALIDATION
==========================================================

[TEST 1] Validating imports...
  All imports successful!

[TEST 2] Validating file structure...
  All required sections present!

[TEST 3] Validating error handling...
  Error handling validated!

[TEST 4] Validating directory structure...
  Directory structure validated!

[TEST 5] Validating metadata structure...
  Metadata structure validated!

==========================================================
  RESULTS: 5/5 tests passed
==========================================================

Validation completed successfully.
```

---

## Advanced Configuration

### Change CLIP model

```python
# In embed_images.py
MODEL_NAME = "ViT-L-14"      # Larger, slower
MODEL_NAME = "ViT-B-32"      # Default, balanced
MODEL_NAME = "ViT-B-16"      # Intermediate
```

Available models:
- `ViT-B-32` (352MB) - Recommended for CPU
- `ViT-B-16` (715MB) - Higher quality
- `ViT-L-14` (1.7GB) - Higher quality, slower
- `ViT-bigG-14` (3.9GB) - Very large

### Change device

```python
# In embed_images.py
DEVICE = "cpu"    # Default
DEVICE = "cuda"   # NVIDIA GPU
DEVICE = "mps"    # Apple Silicon (M1/M2)
```

---

## Troubleshooting

### Error: "No images found in data/images"

```bash
ls data/images/
cp /path/to/images/* data/images/
```

### Error: "No module named 'torch'"

```bash
pip install torch
```

### Error: "CUDA out of memory" (GPU)

```python
DEVICE = "cpu"
```

### Script is slow on CPU

CLIP on CPU is slow (about 3-4 seconds per image).
- Option 1: Use a GPU
- Option 2: Process fewer images
- Option 3: Use a smaller model (ViT-B-16)

---

## Example Use Cases

### 1) Semantic search

```python
import numpy as np
from numpy.linalg import norm

embeddings = np.load('data/embeddings/image_embeddings.npy')
filenames = np.load('data/embeddings/image_filenames.npy')

def cosine_similarity(a, b):
    return np.dot(a, b) / (norm(a) * norm(b))

sim = cosine_similarity(embeddings[0], embeddings[1])
print(f"Similarity: {sim:.3f}")
```

### 2) Unsupervised clustering

```python
from sklearn.cluster import KMeans
import numpy as np

embeddings = np.load('data/embeddings/image_embeddings.npy')
filenames = np.load('data/embeddings/image_filenames.npy')

kmeans = KMeans(n_clusters=5)
clusters = kmeans.fit_predict(embeddings)

for cluster_id in range(5):
    images_in_cluster = filenames[clusters == cluster_id]
    print(f"Cluster {cluster_id}: {images_in_cluster}")
```

### 3) Find similar images

```python
import numpy as np
from numpy.linalg import norm

embeddings = np.load('data/embeddings/image_embeddings.npy')
filenames = np.load('data/embeddings/image_filenames.npy')

def find_similar(query_idx, k=5):
    query_emb = embeddings[query_idx]
    similarities = np.dot(embeddings, query_emb) / norm(embeddings, axis=1) / norm(query_emb)
    top_k = np.argsort(similarities)[::-1][1:k+1]
    return filenames[top_k]

similar = find_similar(0, k=5)
print(f"Similar to {filenames[0]}: {similar}")
```

---

## Notes

1. Privacy: embeddings do not store the original image pixels, only vector representations.
2. Reproducibility: results are deterministic for the same inputs and model.
3. Updates: if you add images, rerun the script to refresh embeddings.
4. Storage: a 512-d embedding uses about 2MB per 1000 images ~2GB.

---

## Next Steps

1. Add text-to-image search (multimodal)
2. Provide a REST API for queries
3. Add batch ingest support
4. Implement embedding cache
5. Build a simple web UI

---

## Support

If you hit issues:
1. Check VALIDATION_REPORT.md
2. Run test_embed_images.py
3. Review execution logs

---

Last updated: December 17, 2025
