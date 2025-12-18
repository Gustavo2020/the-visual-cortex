# The Visual Cortex

A lightweight image-embedding pipeline using OpenAI CLIP, optimized for CPU with clear metrics, simple outputs, and a tiny footprint. Use it to generate embeddings, run quick validation, and plug into downstream tasks like similarity search or clustering.

> For full instructions, see USAGE_GUIDE.md.

## Quick Start

```bash
# 1) Move to project root
cd /home/arcanegus/the-visual-cortex

# 2) (Recommended) Create & activate a virtual env
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3) Install dependencies
pip install -r requirements.txt

# Optional: NVIDIA GPU (CUDA 11.8)
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 4) Prepare images
mkdir -p data/images
# Copy or place .jpg/.jpeg/.png files into data/images

# 5) Run the embedding pipeline
python src/embed_images.py
```

## Directory Layout

```
the-visual-cortex/
├── src/
│   ├── embed_images.py          # Main script (CLIP image embeddings)
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
├── VALIDATION_REPORT.md         # Validation report (generated/maintained by you)
└── USAGE_GUIDE.md               # Detailed usage guide
```

## What You Get

Running `src/embed_images.py` produces:
- `data/embeddings/image_embeddings.npy` — Matrix (N x 512)
- `data/embeddings/image_filenames.npy` — Filenames aligned with embeddings
- `data/embeddings/metadata.json` — Run metadata, timing, memory, failures

Example check:
```python
import numpy as np
emb = np.load('data/embeddings/image_embeddings.npy')
print(emb.shape)  # (N, 512)
```

## Validation

```bash
python src/test_embed_images.py
```
Expected: 5/5 tests pass with structure, imports, errors, and metadata validated.

## Configuration

Inside `src/embed_images.py` you can tweak:
- Model: `MODEL_NAME` (e.g., "ViT-B-32" default, "ViT-B-16", "ViT-L-14")
- Device: `DEVICE` ("cpu", "cuda", "mps")

## Troubleshooting

- No images found: ensure files exist under `data/images/`.
- Missing torch: `pip install torch` (or the CUDA wheel above).
- CUDA OOM: switch `DEVICE = "cpu"` or use fewer images/smaller model.
- Slow on CPU: prefer GPU, fewer images, or a smaller model.

## Next Steps

- Add text-to-image search (multimodal)
- Provide a REST API for queries
- Add batch ingest support
- Implement an embedding cache
- Build a simple web UI

---

For detailed walkthroughs, logs, sample outputs, and advanced options, read USAGE_GUIDE.md.
The Visual Cortex
=================

This repository holds the scripts and utilities I use to bootstrap synthetic image datasets that later feed the training code under `src/` and the experiences in `ui/`. The current workflow is intentionally simple:

1. Download a batch of reference images with `scripts/download_images.py`.
2. Store them under `scripts/data/images` (or any custom directory via `--output-dir`).
3. Consume/transform them from the downstream code in this repo.

## Requirements

The project targets Python 3.10+ and the dependencies listed in `requirements.txt`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Image downloader script

`scripts/download_images.py` automates bulk downloads from Unsplash Source (default) with a few guardrails:

- Configurable retries with exponential backoff via `requests` + `urllib3`.
- MIME/type validation, minimum byte threshold, and per-run SHA-256 hashing to avoid corrupt files.
- Sequential or parallel downloads (see `--workers`) with a `tqdm` progress bar.
- Multiple providers (`unsplash`, `picsum`, or `custom` URLs).

### Basic usage

```bash
python scripts/download_images.py \
  --num-images 200 \
  --width 1024 \
  --height 768 \
  --output-dir /path/to/my/folder
```

The script inspects the target directory, counts the existing images, and only downloads the missing ones to reach the requested total. Useful parameters:

- `--provider`: `unsplash` and `picsum` generate ready-to-use random URLs; `custom` allows an explicit `--url` with `{width}/{height}` placeholders.
- `--min-bytes`: discards responses that are too small to be valid images.
- `--max-attempts`, `--max-seconds`: bound the total effort when the provider keeps failing.
- `--sleep-ok` / `--sleep-fail`: control pauses after successful or failed attempts to honor provider rate limits.
- `--workers`: number of concurrent downloads (keep it low if the provider throttles aggressively).

### Signals and cancellation

Press `Ctrl+C` at any time to stop the downloader. `SIGINT` is intercepted to break the loop gracefully and report how many files were actually saved.

## Data layout

By default images live in `scripts/data/images`. Feel free to create additional subfolders under `scripts/data` to categorize datasets or to plug them into the training pipelines in `src/`.

## Next steps

- Update `requirements.txt` whenever new modules in `src/` or the `ui/` require extra packages.
- Add notebooks or design docs under `docs/` to capture experiments or preprocessing pipelines.
