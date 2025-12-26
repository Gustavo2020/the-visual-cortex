# Production-ready Dockerfile for CLIP Image Search
# Build: docker build -t clip-search .
# Run: docker run -p 8000:8000 -v $(pwd)/data:/app/data clip-search

FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*


# Builder stage
FROM base as builder

# Copy production requirements only
COPY src/requirements.prod.txt requirements.txt

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies (no cache)
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt


# Runtime stage
FROM base as runtime

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ ./src/

# Create data directory for embeddings
RUN mkdir -p /app/data/embeddings

WORKDIR /app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default environment variables
ENV CLIP_MODEL=ViT-B-32 \
    CLIP_PRETRAINED=openai \
    CLIP_DEVICE=cpu \
    LOG_LEVEL=INFO \
    EMBEDDINGS_DIR=/app/data/embeddings

# Non-root user for security
RUN useradd -m -u 1000 clipuser && \
    chown -R clipuser:clipuser /app

USER clipuser

# Expose API port
EXPOSE 8000

# Default command: Run REST API
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
