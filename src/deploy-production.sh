#!/bin/bash
# Production deployment script for CLIP Image Search with HTTPS
# This script sets up and runs the production environment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}CLIP Image Search - Production Deploy${NC}"
echo -e "${BLUE}========================================${NC}"

# ============================================================================
# Configuration
# ============================================================================

# Default values
WORKERS=${WORKERS:-4}
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}
LOG_LEVEL=${LOG_LEVEL:-info}
ENV_FILE=${ENV_FILE:-.env}

# ============================================================================
# Pre-flight Checks
# ============================================================================

echo -e "${BLUE}Running pre-flight checks...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required${NC}"
    exit 1
fi

# Check virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Check dependencies
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install --upgrade pip > /dev/null
    pip install -r requirements.txt > /dev/null
fi

# Check .env file
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Creating $ENV_FILE from template...${NC}"
    cp .env.example "$ENV_FILE"
    echo -e "${RED}⚠️  Please configure $ENV_FILE before deployment${NC}"
    exit 1
fi

# ============================================================================
# SSL Certificate Setup (Let's Encrypt with Certbot)
# ============================================================================

echo -e "${BLUE}Checking SSL certificates...${NC}"

CERT_DIR="${CERT_DIR:-./certs}"
DOMAIN="${DOMAIN:-your-domain.com}"

if [ ! -f "$CERT_DIR/fullchain.pem" ] || [ ! -f "$CERT_DIR/privkey.pem" ]; then
    echo -e "${YELLOW}SSL certificates not found.${NC}"
    echo -e "${YELLOW}To generate with Let's Encrypt:${NC}"
    echo ""
    echo "  sudo certbot certonly --standalone -d $DOMAIN"
    echo "  sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $CERT_DIR/"
    echo "  sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $CERT_DIR/"
    echo "  sudo chown -R \$USER:root $CERT_DIR/"
    echo ""
    echo -e "${YELLOW}Or use self-signed for testing:${NC}"
    echo ""
    echo "  mkdir -p $CERT_DIR"
    echo "  openssl req -x509 -newkey rsa:4096 -keyout $CERT_DIR/privkey.pem -out $CERT_DIR/fullchain.pem -days 365 -nodes"
    echo ""
fi

# ============================================================================
# Application Setup
# ============================================================================

echo -e "${BLUE}Setting up application...${NC}"

# Create necessary directories
mkdir -p logs
mkdir -p data/embeddings
mkdir -p $CERT_DIR

# ============================================================================
# Gunicorn + Uvicorn Workers
# ============================================================================

echo -e "${BLUE}Starting FastAPI with Gunicorn workers...${NC}"
echo "  Gunicorn workers: $WORKERS"
echo "  Host: $HOST:$PORT"
echo "  Log level: $LOG_LEVEL"
echo ""

# Install gunicorn if not present
if ! python3 -c "import gunicorn" 2>/dev/null; then
    echo -e "${YELLOW}Installing gunicorn...${NC}"
    pip install gunicorn > /dev/null
fi

# Start Gunicorn with Uvicorn workers
exec gunicorn \
    --workers $WORKERS \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind $HOST:$PORT \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level $LOG_LEVEL \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    api:app
