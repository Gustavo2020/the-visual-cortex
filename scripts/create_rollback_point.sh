#!/usr/bin/env bash
set -euo pipefail

# Create a rollback point:
# - Tag current Docker images with backup timestamp
# - Backup Nginx site config
# - Archive embeddings and images
# - Record metadata

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
BACKUPS_DIR="$REPO_DIR/data/backups"
NGINX_SITE="/etc/nginx/sites-available/gsx-2.com"

mkdir -p "$BACKUPS_DIR"

echo "Creating rollback point at: $TIMESTAMP"

# Tag Docker images (API/UI)
API_IMG="the-visual-cortex-api"
UI_IMG="the-visual-cortex-ui"

for IMG in "$API_IMG" "$UI_IMG"; do
  if docker image inspect "$IMG" >/dev/null 2>&1; then
    echo "Tagging image $IMG as backup-$TIMESTAMP"
    docker tag "$IMG" "$IMG:backup-$TIMESTAMP"
  else
    echo "Image $IMG not found; skipping tag."
  fi
done

# Backup Nginx site config
if [ -f "$NGINX_SITE" ]; then
  echo "Backing up Nginx config..."
  if sudo cp "$NGINX_SITE" "$NGINX_SITE.bak-$TIMESTAMP"; then
    echo "Nginx backup: $NGINX_SITE.bak-$TIMESTAMP"
  else
    echo "Warning: sudo required to backup Nginx config. Skipping."
  fi
fi

# Archive embeddings and images (small, safe to snapshot)
EMB_ARCH="$BACKUPS_DIR/embeddings-$TIMESTAMP.tar.gz"
IMG_ARCH="$BACKUPS_DIR/images-$TIMESTAMP.tar.gz"

echo "Archiving embeddings..."
tar -C "$REPO_DIR/data" -czf "$EMB_ARCH" embeddings || echo "Embeddings archive failed"
echo "Archiving images..."
tar -C "$REPO_DIR/data" -czf "$IMG_ARCH" images || echo "Images archive failed"

# Metadata
META="$BACKUPS_DIR/rollback-$TIMESTAMP.txt"
{
  echo "timestamp=$TIMESTAMP"
  echo "api_image_backup=${API_IMG}:backup-$TIMESTAMP"
  echo "ui_image_backup=${UI_IMG}:backup-$TIMESTAMP"
  echo "nginx_backup=${NGINX_SITE}.bak-$TIMESTAMP"
  echo "embeddings_archive=$EMB_ARCH"
  echo "images_archive=$IMG_ARCH"
} > "$META"

echo "Rollback point created: $META"
