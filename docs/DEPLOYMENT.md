"""
Production deployment guide and configuration for CLIP Image Search.

This document covers:
1. Installation and requirements
2. Configuration management
3. Running the search service
4. API usage examples
5. Monitoring and logging
6. Docker deployment
7. Performance tuning
"""

# ============================================================================
# REQUIREMENTS & INSTALLATION
# ============================================================================

# requirements.txt
"""
# Core dependencies
numpy>=1.21.0
torch>=1.9.0
open-clip-torch>=2.0.0
Pillow>=8.0.0
psutil>=5.8.0
tqdm>=4.50.0

# For REST API
fastapi>=0.95.0
uvicorn>=0.21.0
pydantic>=1.9.0
python-multipart>=0.0.5

# For testing
pytest>=7.0.0
pytest-asyncio>=0.20.0
pytest-cov>=3.0.0

# Development
black>=22.0.0
flake8>=4.0.0
mypy>=0.950
"""

# Installation:
# pip install -r requirements.txt


# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

# .env file example:
"""
# CLIP Model Configuration
CLIP_MODEL=ViT-B-32
CLIP_PRETRAINED=openai
CLIP_DEVICE=cpu

# Embeddings Configuration
EMBEDDINGS_DIR=./data/embeddings

# Search Service Configuration
SEARCH_TOP_K=5

# Logging Configuration
LOG_LEVEL=INFO
"""


# ============================================================================
# RUNNING THE SERVICE
# ============================================================================

# 1. Interactive CLI (Development/Testing)
# python search.py

# 2. REST API (Production)
# uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4

# 3. With Gunicorn (Production)
# gunicorn -w 4 -k uvicorn.workers.UvicornWorker api:app --bind 0.0.0.0:8000


# ============================================================================
# API USAGE EXAMPLES
# ============================================================================

# Curl examples:

# Health check:
# curl http://localhost:8000/health

# POST request (JSON):
# curl -X POST http://localhost:8000/search \
#   -H "Content-Type: application/json" \
#   -d '{"query":"a red car", "top_k":5}'

# GET request (Query parameters):
# curl "http://localhost:8000/search?query=a+red+car&top_k=5"


# Python client example:
"""
import requests

API_URL = "http://localhost:8000"

def search_images(query: str, top_k: int = 5):
    response = requests.post(
        f"{API_URL}/search",
        json={"query": query, "top_k": top_k}
    )
    response.raise_for_status()
    return response.json()

# Usage
results = search_images("a sunny beach", top_k=10)
for result in results["results"]:
    print(f"{result['filename']}: {result['similarity']:.4f}")
"""


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

"""
Logging is configured with structured format:
    %(asctime)s - %(name)s - %(levelname)s - %(message)s

Log levels:
- DEBUG: Detailed search operations, model loading
- INFO: Search queries, service initialization
- WARNING: Invalid queries, missing files
- ERROR: Search failures, model errors
- CRITICAL: Service initialization failures

To enable debug logging, set LOG_LEVEL environment variable:
    export LOG_LEVEL=DEBUG
"""


# ============================================================================
# DOCKER DEPLOYMENT
# ============================================================================

# Dockerfile example:
"""
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY data/embeddings ./data/embeddings

WORKDIR /app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run API server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
"""

# Docker Compose example:
"""
version: '3.8'

services:
  clip-search:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CLIP_DEVICE=cpu
      - CLIP_MODEL=ViT-B-32
      - LOG_LEVEL=INFO
    volumes:
      - ./data/embeddings:/app/data/embeddings:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
"""


# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

"""
1. Device Selection:
   - CPU: Good for development, low memory requirements
   - GPU (CUDA): 10-20x faster for inference
   
   Set via environment:
   export CLIP_DEVICE=cuda

2. Model Selection:
   Available models (sorted by size):
   - ViT-B-32: Smallest, fastest (default)
   - ViT-B-16: Larger, more accurate
   - ViT-L-14: Largest, most accurate
   
   Set via environment:
   export CLIP_MODEL=ViT-L-14

3. Worker Configuration:
   For multi-core systems, increase workers:
   uvicorn api:app --workers 8
   
   Recommended: workers = cpu_count

4. Embeddings Pre-computation:
   Pre-compute all embeddings offline to avoid
   inference latency during search operations.
   
   See embed_images.py for preprocessing pipeline.

5. Memory Optimization:
   - Use model.eval() to disable dropout/batchnorm
   - Pre-normalize embeddings to avoid recomputation
   - Cache model in memory (already done in this implementation)

6. Caching:
   For repeated queries, implement Redis caching:
   
   import redis
   cache = redis.Redis(host='localhost', port=6379)
   key = f"search:{query}"
   cached = cache.get(key)
   if cached:
       return json.loads(cached)
"""


# ============================================================================
# MONITORING & OBSERVABILITY
# ============================================================================

"""
1. Health Checks:
   GET /health - Returns service status and configuration
   
2. Request Logging:
   All search requests are logged with:
   - Query text
   - Number of results (top_k)
   - Execution time
   
3. Error Monitoring:
   Implement error tracking (e.g., Sentry):
   
   import sentry_sdk
   sentry_sdk.init("https://key@sentry.io/project")

4. Performance Metrics:
   Add metrics collection (e.g., Prometheus):
   
   from prometheus_client import Counter, Histogram
   
   search_requests = Counter('search_requests_total', 'Total searches')
   search_latency = Histogram('search_latency_seconds', 'Search latency')

5. Logging with ELK Stack:
   Forward logs to Elasticsearch for analysis:
   
   import logging.handlers
   handler = logging.handlers.SocketHandler('logstash:5000')
"""


# ============================================================================
# SECURITY CONSIDERATIONS
# ============================================================================

"""
1. Input Validation:
   ✓ Query length limits (2-512 characters)
   ✓ Type checking (string only)
   ✓ Whitespace validation
   
   Additional recommendations:
   - Implement rate limiting per IP/user
   - Add request size limits
   - Validate top_k parameter range

2. Authentication:
   Add API key authentication:
   
   from fastapi.security import HTTPBearer, HTTPAuthCredentials
   
   security = HTTPBearer()
   
   @app.post("/search")
   async def search(request: SearchRequest, credentials: HTTPAuthCredentials = Depends(security)):
       if not validate_api_key(credentials.credentials):
           raise HTTPException(status_code=403)

3. CORS Configuration:
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://trusted-domain.com"],
       allow_credentials=True,
       allow_methods=["POST", "GET"],
       allow_headers=["*"]
   )

4. Rate Limiting:
   from slowapi import Limiter
   from slowapi.util import get_remote_address
   
   limiter = Limiter(key_func=get_remote_address)
   
   @app.post("/search")
   @limiter.limit("100/minute")
   async def search(request: SearchRequest):
       ...

5. HTTPS:
   Use reverse proxy (Nginx) with SSL certificates:
   
   server {
       listen 443 ssl http2;
       ssl_certificate /etc/nginx/certs/cert.pem;
       
       location / {
           proxy_pass http://localhost:8000;
       }
   }
"""


# ============================================================================
# TROUBLESHOOTING
# ============================================================================

"""
1. Model Loading Fails:
   Error: "Model loading failed"
   - Check CLIP_MODEL is valid
   - Ensure internet connection for downloading pretrained weights
   - Check disk space for model cache

2. Embeddings Not Found:
   Error: "Embeddings file not found"
   - Verify EMBEDDINGS_DIR path exists
   - Run embed_images.py to generate embeddings
   - Check file permissions

3. Memory Issues:
   - Use ViT-B-32 (smaller model)
   - Switch from GPU to CPU if out of VRAM
   - Check for memory leaks in production monitoring

4. Slow Search Performance:
   - Use GPU device (CLIP_DEVICE=cuda)
   - Use larger model for batch processing
   - Check embeddings are pre-normalized

5. API Not Responding:
   - Check uvicorn process is running
   - Verify port 8000 is not in use
   - Check logs for errors
   - Restart service: pkill uvicorn
"""


# ============================================================================
# TESTING
# ============================================================================

"""
Unit Tests:
    pytest test_search.py -v
    pytest test_search.py -v --cov=search

Specific test class:
    pytest test_search.py::TestQueryValidation -v

With coverage report:
    pytest test_search.py --cov=search --cov-report=html

Integration tests:
    pytest -m integration

Load testing:
    locust -f locustfile.py --host=http://localhost:8000
"""


# ============================================================================
# DEPLOYMENT CHECKLIST
# ============================================================================

"""
[ ] Install dependencies: pip install -r requirements.txt
[ ] Set environment variables (.env file)
[ ] Pre-compute embeddings: python embed_images.py
[ ] Run unit tests: pytest test_search.py -v
[ ] Check logging configuration
[ ] Set up health checks and monitoring
[ ] Configure rate limiting
[ ] Set up error tracking (Sentry, etc.)
[ ] Configure SSL/HTTPS with reverse proxy
[ ] Add authentication (API keys, JWT)
[ ] Set up log aggregation (ELK, etc.)
[ ] Performance testing with expected load
[ ] Document API endpoints
[ ] Set up CI/CD pipeline
[ ] Configure auto-scaling if using containers
[ ] Plan rollback strategy
[ ] Schedule regular backups of embeddings
"""
