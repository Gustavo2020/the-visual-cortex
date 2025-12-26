# The Visual Cortex

Production-ready semantic image search system using OpenAI CLIP, SigLIP, and other open-clip models with REST API, comprehensive testing, and deployment guides for HTTPS environments.

**Features:**
- Semantic text-to-image search with configurable CLIP/SigLIP embeddings (no hardcoding)
- Multi-model support: ViT-B-32, ViT-L-14, ViT-H-14, ViT-SO400M-14-SigLIP, EVA02, and 60+ more
- FastAPI REST API with automatic documentation (Swagger)
- HTTPS-ready with Nginx reverse proxy and Let's Encrypt SSL
- Multi-worker deployment (Gunicorn + Uvicorn)
- Production-grade error handling, logging, and validation
- Docker and Docker Compose for easy deployment
- Comprehensive test suite (40+ unit tests)
- Performance optimized (CPU and GPU support)
- Rate limiting, security headers, and health checks
- NEW: Hash-based deduplication for downloaded images (SHA-256)
- NEW: Automatic image download without overwrites or duplicates

---

## Operational Runbook (gsx-2.com)

For day-to-day operations of the deployment at gsx-2.com, see:
- [docs/RUNBOOK_GSX2.md](docs/RUNBOOK_GSX2.md)

---

## Quick Start

### Development (CLI Interface)

```bash
# 1) Navigate to project
cd /home/arcanegus/the-visual-cortex

# 2) Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3) Install dependencies
pip install -r src/requirements.txt

# 4) Prepare images (if needed)
mkdir -p data/images
# Copy .jpg/.jpeg/.png files to data/images
python src/embed_images.py

# 5) Run interactive CLI search
python src/search.py
```

### Production (REST API with HTTPS)

```bash
# 1) Install system dependencies
sudo apt-get update
sudo apt-get install -y nginx certbot python3-venv

# 2) Generate SSL certificates
sudo certbot certonly --standalone -d your-domain.com

# 3) Copy certificates
mkdir -p certs
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem certs/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem certs/

# 4) Update Nginx configuration
sed -i 's/your-domain.com/your-actual-domain/g' src/nginx.conf

# 5) Deploy with Docker Compose
docker-compose -f src/docker-compose.production.yml up -d

# 6) Verify deployment
curl https://your-domain.com/health
```

---

## Project Architecture

### System Architecture (Production)

```
Client (Browser/API)
https://your-domain.com
       |
       | HTTPS (Port 443)
       | SSL/TLS + Security Headers
       v
Nginx Reverse Proxy
- SSL/TLS Termination
- Rate Limiting
- Gzip Compression
- Load Balancing
       |
       | HTTP (Port 8000)
       | Internal Connection
       v
Gunicorn (App Server)
- 4-8 Uvicorn Workers
- Multi-Process
- Graceful Restart
       |
       v
FastAPI Application
- /search - Text search
- /health - Health check
- /docs - Swagger UI
- Automatic validation
       |
       v
CLIP Search Engine
- Semantic search
- Model caching
- Error handling
- Logging
```

### Component Overview

| Component | Purpose | Technology |
|-----------|---------|-----------|
| Nginx | Reverse proxy, SSL/TLS, rate limiting | Nginx 1.21+ |
| Gunicorn | Application server, worker management | Gunicorn 20.1+ |
| FastAPI | REST API framework | FastAPI 0.95+ |
| Uvicorn | ASGI server for FastAPI | Uvicorn 0.21+ |
| CLIP | Image-text embedding model | OpenAI CLIP / open-clip |
| PyTorch | Deep learning framework | PyTorch 1.9+ |
| Docker | Containerization | Docker 20.10+ |

---

## Directory Layout

```
the-visual-cortex/
|
+-- src/
|   +-- CORE MODULES
|   |   +-- api.py                      # FastAPI REST API (321 lines)
|   |   +-- search.py                   # CLIP search engine (362 lines)
|   |   +-- embed_images.py             # Image embedding pipeline
|   |
|   +-- TESTING
|   |   +-- test_search.py              # Search module tests (400+ lines)
|   |   +-- test_embed_images.py        # Embedding tests
|   |
|   +-- DEPLOYMENT
|   |   +-- Dockerfile                  # Container image
|   |   +-- docker-compose.yml          # Development stack
|   |   +-- docker-compose.production.yml  # Production stack
|   |   +-- nginx.conf                  # Nginx configuration (346 lines)
|   |   +-- clip-search-api.service     # Systemd service
|   |   +-- deploy-production.sh        # Deployment script
|   |
|   +-- DOCUMENTATION
|   |   +-- requirements.txt            # Python dependencies
|   |   +-- README.md                   # This file
|   |   +-- DEPLOYMENT.md               # General deployment guide
|   |   +-- HTTPS_DEPLOYMENT_GUIDE.md   # HTTPS setup guide
|   |   +-- HTTPS_FASTAPI_RECOMMENDATIONS.md  # Architecture guide
|   |   +-- HTTPS_ESPANOL.md            # Spanish quick guide
|   |   +-- CERTIFICATE_SETUP.md        # SSL certificate guide
|   |   +-- IMPROVEMENTS.md             # Technical improvements
|   |   +-- .env.example                # Environment variables
|   |
|   +-- CONFIGURATION
|       +-- .env                        # Environment config (create from .env.example)
|
+-- data/
|   +-- images/                         # Input images directory
|   +-- embeddings/                     # Pre-computed embeddings
|       +-- image_embeddings.npy
|       +-- image_filenames.npy
|
+-- certs/                              # SSL certificates (for HTTPS)
|   +-- fullchain.pem
|   +-- privkey.pem
|   +-- chain.pem
|
+-- logs/                               # Application logs
|   +-- api/
|   +-- nginx/
|
+-- README.md                           # Root readme (this file)
```

---

## Deployment Options

### Option 1: Docker Compose (Recommended)

Best for production deployments, easy scaling, and reproducible environments.

```bash
# Development stack
docker-compose -f src/docker-compose.yml up -d

# Production stack (with HTTPS and Nginx)
docker-compose -f src/docker-compose.production.yml up -d
```

### Option 2: Systemd Service (Linux)

Best for direct server deployment, maximum control, and lower overhead.

```bash
# Setup
sudo cp src/clip-search-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start clip-search-api
sudo systemctl enable clip-search-api
```

### Option 3: Kubernetes

Best for large-scale, multi-region deployments and auto-scaling.

---

## Dependencies and Requirements

### Core Dependencies
- PyTorch (1.9+) - Deep learning framework
- OpenAI CLIP / open-clip-torch (2.0+) - Image-text embeddings
- NumPy (1.21+) - Numerical computing
- Pillow (8.0+) - Image processing

### API Framework
- FastAPI (0.95+) - REST API framework
- Uvicorn (0.21+) - ASGI server
- Pydantic (1.9+) - Data validation

### Production
- Gunicorn (20.1+) - Application server
- Nginx (1.21+) - Reverse proxy
- Docker (20.10+) - Containerization

### Testing
- Pytest (7.0+) - Testing framework
- Pytest-cov (3.0+) - Code coverage
- pytest-asyncio (0.20+) - Async testing

### Development
- Black (22.0+) - Code formatter
- Flake8 (4.0+) - Linter
- Mypy (0.950+) - Type checker
- isort (5.10+) - Import sorter

See requirements.txt for complete list and versions.

---

## API Endpoints

### Search Images
```http
POST /search
Content-Type: application/json

{
  "query": "a red car on a sunny day",
  "top_k": 5
}

Response:
{
  "query": "a red car on a sunny day",
  "total_results": 5,
  "results": [
    {
      "filename": "image1.jpg",
      "similarity": 0.8341
    },
    ...
  ]
}
```

### Health Check
```http
GET /health

Response:
{
  "status": "healthy",
  "model": "ViT-B-32",
  "device": "cpu",
  "num_images": 1000
}
```

### API Documentation
```http
GET /docs    # Swagger UI
GET /redoc   # ReDoc UI
```

---

## Security Features

HTTPS/TLS
- Let's Encrypt certificate support
- Auto-renewal with certbot
- TLS 1.2 + 1.3 only

Rate Limiting
- Per-endpoint limits
- Connection limiting
- Graceful degradation

Input Validation
- Query length limits (2-512 characters)
- Type checking
- Sanitization

Security Headers
- HSTS (Strict Transport Security)
- CSP (Content Security Policy)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection

Access Control
- Ready for API key authentication
- CORS configurable
- Non-root Docker user

---

## Performance Characteristics

### Latency

| Device | Model | Latency |
|--------|-------|---------|
| CPU (i7) | ViT-B-32 | 100-150ms |
| CPU (i7) | ViT-L-14 | 200-300ms |
| GPU (RTX 3080) | ViT-B-32 | 5-15ms |
| GPU (RTX 3080) | ViT-L-14 | 10-20ms |

### Throughput (with Nginx + 4 workers)

| Device | Configuration | Throughput |
|--------|---------------|-----------|
| CPU | ViT-B-32 | 20-40 req/s |
| GPU | ViT-B-32 | 100+ req/s |

### Memory Requirements

| Component | Memory |
|-----------|--------|
| Nginx | ~50MB |
| Gunicorn (4 workers) | ~800MB |
| FastAPI app | ~200MB |
| CLIP Model (ViT-B-32) | ~350MB |
| **Total** | **~1.4GB minimum** |

---

## Configuration & Model Selection

### Supported Models (via open-clip)

| Model | Pretrained | Dimension | Speed (CPU) | Quality |
|-------|-----------|-----------|-------------|---------|
| **ViT-B-32** | openai | 512 | Very Fast | Good |
| **ViT-B-16** | openai | 512 | Fast | Better |
| **ViT-L-14** | openai | 768 | Medium | Better |
| **ViT-H-14** | laion2b | 1024 | Slow | Excellent |
| **EVA02-L-14** | merged2b | 768 | Medium | Better |
| **ViT-SO400M-14-SigLIP** | webli | 1152 | Slow | Excellent |
| **ViT-B-16-SigLIP** | webli | 512 | Fast | Better |
| **ViT-L-16-SigLIP** | webli | 768 | Medium | Excellent |

### Environment Variables

Configure models **without hardcoding** using environment variables:

```bash
# Model selection
export CLIP_MODEL="ViT-SO400M-14-SigLIP-384"        # Model name
export CLIP_PRETRAINED="webli"                       # Checkpoint source
export CLIP_TOKENIZER="ViT-SO400M-14-SigLIP-384"   # Optional: tokenizer (auto-detected if omitted)
export CLIP_DEVICE="cpu"                             # Device: cpu or cuda
export CLIP_DTYPE="auto"                             # Data type: auto, float32, float16

# Embeddings & search
export EMBEDDINGS_DIR="./data/embeddings"           # Embedding storage path
export SEARCH_TOP_K="5"                              # Default results count
export NORMALIZE_EMBEDDINGS="1"                      # L2 normalization (0/1)
```

---

## Usage: Embedding & Search

### Step 1: Generate Embeddings (CLIP/SigLIP)

**CPU with ViT-SO400M-14-SigLIP-384 (recommended):**
```bash
cd /home/arcanegus/the-visual-cortex
source venv/bin/activate
pip install -r src/requirements.txt transformers  # transformers required for SigLIP tokenizers

export CLIP_MODEL="ViT-SO400M-14-SigLIP-384"
export CLIP_PRETRAINED="webli"
export CLIP_TOKENIZER="ViT-SO400M-14-SigLIP-384"
python src/embed_images.py
```

**GPU (CUDA):**
```bash
export CLIP_MODEL="ViT-SO400M-14-SigLIP-384"
export CLIP_PRETRAINED="webli"
export CLIP_DEVICE="cuda"
python src/embed_images.py  # ~20x faster
```

**Lightweight option (ViT-L-14 CLIP):**
```bash
export CLIP_MODEL="ViT-L-14"
export CLIP_PRETRAINED="openai"
python src/embed_images.py
```

### Step 2: Download Images (Optional)

```bash
cd /home/arcanegus/the-visual-cortex/scripts

# Unsplash (quality random images)
python download_images.py --provider unsplash --num-images 500 --width 800 --height 600

# Picsum (fast random placeholders)
python download_images.py --provider picsum --num-images 1000 --width 1024 --height 768 --workers 8

# Custom source with placeholders
python download_images.py --provider custom \
  --url "https://example.com/api/image?w={width}&h={height}" \
  --num-images 200 --min-bytes 30000
```

**Features:**
- Automatic deduplication (SHA-256 hashing)
- No overwrites (UUID-based unique filenames)
- Concurrent downloads (--workers N)
- Target `data/images` in repository root automatically

### Step 3: Run Interactive Search (CLI)

```bash
export CLIP_MODEL="ViT-SO400M-14-SigLIP-384"
export CLIP_PRETRAINED="webli"
python src/search.py
```

Example interaction:
```
Query: running in the snow
Results:
  1. IMG_abc123.jpg (0.87)
  2. IMG_def456.jpg (0.85)
  3. IMG_ghi789.jpg (0.82)
```

### Step 4: Run REST API (Production)

```bash
export CLIP_MODEL="ViT-SO400M-14-SigLIP-384"
export CLIP_PRETRAINED="webli"
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

**Access:**
- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Search: POST http://localhost:8000/search

**Example cURL:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "sunset over mountains", "top_k": 5}'
```

**Example Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/search",
    json={"query": "dancing in the rain", "top_k": 10}
)
results = response.json()
for result in results["results"]:
    print(f"{result['filename']}: {result['similarity']:.4f}")
```

---

## Recent Updates (December 18, 2025)

### Model Flexibility (search.py, embed_images.py)
- **Removed hardcoded models**: Now uses environment variables for full flexibility
- **SigLIP support**: Added `CLIP_TOKENIZER` env variable for model-specific tokenizers
- **Tokenizer fallback**: Graceful degradation if HuggingFace transformers unavailable
- **60+ models**: Support for open-clip's entire catalog (CLIP, SigLIP, EVA, MobileCLIP, etc.)

**Code changes:**
```python
# Config class now includes:
TOKENIZER_NAME: Optional[str] = os.getenv("CLIP_TOKENIZER")

# Tokenizer initialization:
tokenizer_name = self.config.TOKENIZER_NAME or self.config.MODEL_NAME
try:
    self.tokenizer = open_clip.get_tokenizer(tokenizer_name)
except Exception:
    self.tokenizer = open_clip.tokenize  # Fallback
```

### Image Download Improvements (download_images.py)
- **SHA-256 deduplication**: Avoids downloading identical images (by content hash)
- **No overwrites**: UUID-based filenames prevent collision overwrites
- **Automatic repo path**: Defaults to `data/images` at repository root (no need for --output-dir)
- **Semantics fix**: `--num-images` now means "download N new images" (not total target)
- **Concurrent safety**: Hash tracking thread-safe with worker pools (--workers N)

**Code changes:**
```python
# Load existing hashes on startup
existing_hashes = load_existing_hashes(output_dir)

# Check for duplicates before saving
file_hash = sha256_bytes(data)
if file_hash in existing_hashes:
    return None  # Skip duplicate
existing_hashes.add(file_hash)

# Unique naming with collision retry
for _ in range(5):
    candidate = dest_dir / f"{prefix}{uuid.uuid4().hex[:8]}{ext}"
    if not candidate.exists():
        path = candidate
        break
```

### Dependencies
Added optional support:
```bash
pip install transformers>=4.37.0  # For SigLIP/HF tokenizers (optional but recommended)
```

---

## API Reference

### POST /search

**Request:**
```json
{
  "query": "text description of images",
  "top_k": 5
}
```

**Response:**
```json
{
  "query": "text description",
  "total_results": 5,
  "results": [
    {"filename": "IMG_abc123.jpg", "similarity": 0.8765},
    {"filename": "IMG_def456.jpg", "similarity": 0.8543}
  ]
}
```

### GET /health

**Response:**
```json
{
  "status": "healthy",
  "model": "ViT-SO400M-14-SigLIP-384",
  "device": "cpu",
  "num_images": 2006
}
```

### GET /images/{filename}

Returns the image file for display/download.

---

##  Configuration

### Environment Variables

Create `.env` file from `.env.example`:

```bash
# CLIP Model Configuration
CLIP_MODEL=ViT-B-32              # Options: ViT-B-32, ViT-B-16, ViT-L-14
CLIP_PRETRAINED=openai            # Pretrained weights source
CLIP_DEVICE=cpu                    # cpu or cuda (for GPU)

# Embeddings
EMBEDDINGS_DIR=./data/embeddings   # Path to embeddings

# Search
SEARCH_TOP_K=5                      # Default number of results

# Logging
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR
```

See [.env.example](src/.env.example) for all options.

---

##  Documentation Guide

| Document | Purpose |
|----------|---------|
| **README.md** (this file) | Overview and quick start |
| **src/DEPLOYMENT.md** | General deployment guide |
| **src/HTTPS_DEPLOYMENT_GUIDE.md** | Step-by-step HTTPS setup |
| **src/HTTPS_FASTAPI_RECOMMENDATIONS.md** | Architecture recommendations |
| **src/HTTPS_ESPANOL.md** | Spanish quick guide |
| **src/CERTIFICATE_SETUP.md** | SSL certificate management |
| **src/IMPROVEMENTS.md** | Technical improvements summary |
| **USAGE_GUIDE.md** | Original usage documentation |

---

##  Troubleshooting

### Embeddings Not Found
```bash
# Generate embeddings
cd src
python embed_images.py
```

### API Not Responding
```bash
# Check service status (Docker)
docker-compose -f src/docker-compose.production.yml ps

# Check logs
docker-compose -f src/docker-compose.production.yml logs -f api

# Verify health
curl https://your-domain.com/health
```

### HTTPS Certificate Issues
```bash
# Verify certificate
openssl s_client -connect your-domain.com:443

# Check expiration
certbot certificates

# Renew manually
sudo certbot renew
```

### Rate Limiting Too Strict
Edit `src/nginx.conf` and adjust rate limits:
```nginx
limit_req_zone $binary_remote_addr zone=search_limit:10m rate=10r/s;
```

---

##  Updates & Maintenance

### Upgrade Dependencies
```bash
pip install --upgrade -r src/requirements.txt
```

### Update CLIP Model
```bash
# In .env, change CLIP_MODEL to ViT-B-16 or ViT-L-14
CLIP_MODEL=ViT-L-14
```

### Renew SSL Certificates
```bash
sudo certbot renew --force-renewal
# Then restart services
docker-compose -f src/docker-compose.production.yml restart
```

---

##  Pre-Deployment Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r src/requirements.txt`)
- [ ] Data/embeddings prepared
- [ ] `.env` file created from `.env.example`
- [ ] Tests passing (`pytest src/test_search.py -v`)
- [ ] (Production) Domain registered
- [ ] (Production) Ports 80 & 443 open
- [ ] (Production) SSL certificates generated
- [ ] (Production) nginx.conf configured with domain
- [ ] (Production) Docker & docker-compose installed

---

##  Learning Resources

- [CLIP Paper](https://arxiv.org/abs/2103.14030)
- [OpenAI CLIP](https://github.com/openai/clip)
- [Open CLIP](https://github.com/mlfoundations/open_clip)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)

---

##  Support

For issues or questions:
1. Check relevant documentation (links above)
2. Review test cases in `test_search.py`
3. Check logs for error messages
4. See troubleshooting section

---

##  License

[Add your license]

---

##  Contributing

Contributions welcome! Please ensure:
- Tests pass: `pytest src/test_search.py -v`
- Code formatted: `black src/`
- Type hints included
- Documentation updated

---

**Last Updated:** December 2025  
**Status:** Production-Ready 

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
