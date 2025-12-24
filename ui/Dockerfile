# Dockerfile for Streamlit UI
# Build: docker build -t visual-cortex-ui -f ui/Dockerfile .
# Run: docker run -p 8501:8501 -e API_HOST=localhost -e API_PORT=8000 visual-cortex-ui

FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY src/requirements.txt requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install streamlit

# Copy application code
COPY ui/app.py ./app.py

# Create non-root user
RUN useradd -m -u 1000 streamlit && \
    chown -R streamlit:streamlit /app

USER streamlit

# Expose Streamlit port
EXPOSE 8501

# Streamlit config
RUN mkdir -p ~/.streamlit && \
    echo "[server]\nheadless = true\nport = 8501\nenableXsrfProtection = false\n[logger]\nlevel = \"info\"" > ~/.streamlit/config.toml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
