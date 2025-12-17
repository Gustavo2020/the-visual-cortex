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
