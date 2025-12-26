#!/usr/bin/env bash
set -euo pipefail

# Restore from latest rollback point:
# - Restore Nginx site config
# - Retag backup images back to :latest
# - Recreate containers

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
BACKUPS_DIR="$REPO_DIR/data/backups"
NGINX_SITE="/etc/nginx/sites-available/gsx-2.com"

# Get latest rollback metadata
LATEST_META="$(ls -1t "$BACKUPS_DIR"/rollback-*.txt 2>/dev/null | head -n 1 || true)"
if [ -z "${LATEST_META:-}" ]; then
  echo "No rollback metadata found." >&2
  exit 1
fi
echo "Using rollback metadata: $LATEST_META"

# Parse metadata
TIMESTAMP="$(grep '^timestamp=' "$LATEST_META" | cut -d'=' -f2)"
API_BACKUP="$(grep '^api_image_backup=' "$LATEST_META" | cut -d'=' -f2)"
UI_BACKUP="$(grep '^ui_image_backup=' "$LATEST_META" | cut -d'=' -f2)"
NGINX_BACKUP="$(grep '^nginx_backup=' "$LATEST_META" | cut -d'=' -f2)"

echo "Timestamp: $TIMESTAMP"
echo "API backup tag: $API_BACKUP"
echo "UI backup tag: $UI_BACKUP"
echo "Nginx backup file: $NGINX_BACKUP"

# Restore Nginx config
if [ -f "$NGINX_BACKUP" ]; then
  echo "Restoring Nginx config from $NGINX_BACKUP..."
  if sudo cp "$NGINX_BACKUP" "$NGINX_SITE"; then
    sudo nginx -t && sudo systemctl reload nginx || echo "Nginx reload failed"
  else
    echo "Failed to restore Nginx config; try running with sudo." >&2
  fi
else
  echo "Nginx backup not found; skipping." >&2
fi

# Retag images back to latest
if docker image inspect "$API_BACKUP" >/dev/null 2>&1; then
  echo "Retagging API image to latest"
  docker tag "$API_BACKUP" the-visual-cortex-api:latest
fi
if docker image inspect "$UI_BACKUP" >/dev/null 2>&1; then
  echo "Retagging UI image to latest"
  docker tag "$UI_BACKUP" the-visual-cortex-ui:latest
fi

# Recreate containers
echo "Restarting containers..."
docker stop visual-cortex-api visual-cortex-ui >/dev/null 2>&1 || true
docker rm visual-cortex-api visual-cortex-ui >/dev/null 2>&1 || true

# Ensure Docker network exists
docker network create visual-cortex-net 2>/dev/null || true

docker run -d --name visual-cortex-api --network visual-cortex-net \
  -p 127.0.0.1:8000:8000 \
  -e CLIP_MODEL=ViT-B-32 -e CLIP_PRETRAINED=openai -e CLIP_DEVICE=cpu \
  -e EMBEDDINGS_DIR=/app/data/embeddings \
  -v "$REPO_DIR/data/embeddings:/app/data/embeddings:ro" \
  -v "$REPO_DIR/data/images:/app/data/images:ro" \
  the-visual-cortex-api:latest

docker run -d --name visual-cortex-ui --network visual-cortex-net \
  -p 127.0.0.1:8501:8501 \
  -e API_HOST=visual-cortex-api -e API_PORT=8000 \
  -e STREAMLIT_BASE_URL_PATH=the-visual-cortex \
  the-visual-cortex-ui:latest

echo "Rollback completed."
