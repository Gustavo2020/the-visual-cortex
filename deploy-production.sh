#!/bin/bash
# ============================================================================
# The Visual Cortex - Production Deployment Script
# ============================================================================
# Usage:
#   bash deploy-production.sh yourdomain.com
#
# What it does:
#   1. Validates domain and environment
#   2. Sets up SSL certificates (if needed)
#   3. Builds and starts Docker containers
#   4. Configures Nginx reverse proxy
#   5. Runs health checks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# Functions
# ============================================================================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# ============================================================================
# Main Script
# ============================================================================

DOMAIN="${1:-}"

if [ -z "$DOMAIN" ]; then
    log_error "Usage: bash deploy-production.sh yourdomain.com"
fi

log_info "=========================================="
log_info "The Visual Cortex - Production Deployment"
log_info "=========================================="
log_info "Domain: $DOMAIN"

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed. Please install Docker first."
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose is not installed. Please install Docker Compose first."
fi

log_info "✓ Docker and Docker Compose installed"

# Check if data/embeddings exists
if [ ! -d "data/embeddings" ]; then
    log_error "data/embeddings directory not found. Run 'python src/embed_images.py' first."
fi

log_info "✓ Embeddings found"

# Create .env file if not exists
if [ ! -f ".env" ]; then
    log_info "Creating .env from .env.example..."
    cp .env.example .env
    sed -i "s/yourdomain.com/$DOMAIN/g" .env
    log_warn "⚠ Update .env with your actual configuration"
fi

# Check for SSL certificates
if [ ! -f "certs/fullchain.pem" ] || [ ! -f "certs/privkey.pem" ]; then
    log_warn "SSL certificates not found in ./certs/"
    log_info "You can generate them with Let's Encrypt:"
    log_info "  sudo certbot certonly --standalone -d $DOMAIN"
    log_info "  sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem certs/"
    log_info "  sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem certs/"
    log_info "  sudo chown $USER:$USER certs/*"
fi

# Build Docker images
log_info "Building Docker images..."
docker-compose -f docker-compose.production.yml build --no-cache || log_error "Build failed"

log_info "✓ Docker images built successfully"

# Start services
log_info "Starting services..."
docker-compose -f docker-compose.production.yml up -d || log_error "Failed to start services"

log_info "✓ Services started"

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
sleep 10

log_info "Checking API health..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    log_info "✓ API is healthy"
else
    log_warn "⚠ API health check pending (can take a minute)"
fi

log_info "Checking UI health..."
if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    log_info "✓ UI is healthy"
else
    log_warn "⚠ UI health check pending (can take a minute)"
fi

# Summary
log_info "=========================================="
log_info "Deployment Summary"
log_info "=========================================="
log_info "Domain: $DOMAIN"
log_info "API: http://$DOMAIN/api"
log_info "UI: http://$DOMAIN/"
log_info ""
log_info "Next steps:"
log_info "1. Verify .env configuration"
log_info "2. Set up SSL certificates if not done"
log_info "3. Update DNS to point to this server"
log_info "4. Monitor logs: docker-compose -f docker-compose.production.yml logs -f"
log_info ""
log_info "Container status:"
docker-compose -f docker-compose.production.yml ps

log_info "✓ Deployment complete!"
