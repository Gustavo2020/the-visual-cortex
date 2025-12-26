#!/usr/bin/env bash
set -euo pipefail

# Backup critical assets before cleanup so we can rollback if needed.
# - data/cache -> data/backups/cache-<timestamp>.tar.gz
# - /etc/nginx/sites-available/gsx-2.com -> .bak-<timestamp>

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
BACKUPS_DIR="$REPO_DIR/data/backups"
CACHE_DIR="$REPO_DIR/data/cache"
NGINX_SITE="/etc/nginx/sites-available/gsx-2.com"

mkdir -p "$BACKUPS_DIR"

echo "Backup timestamp: $TIMESTAMP"

# Backup data/cache (contents only)
if [ -d "$CACHE_DIR" ]; then
  echo "Backing up cache directory..."
  tar -C "$REPO_DIR/data" -czf "$BACKUPS_DIR/cache-$TIMESTAMP.tar.gz" cache
  echo "Cache backup: $BACKUPS_DIR/cache-$TIMESTAMP.tar.gz"
else
  echo "Cache dir not found; skipping cache backup."
fi

# Backup Nginx site config
if [ -f "$NGINX_SITE" ]; then
  echo "Backing up Nginx site config..."
  if sudo cp "$NGINX_SITE" "$NGINX_SITE.bak-$TIMESTAMP"; then
    echo "Nginx backup: $NGINX_SITE.bak-$TIMESTAMP"
  else
    echo "Could not backup Nginx config without sudo. Run this script with sudo to include Nginx backup."
  fi
else
  echo "Nginx site config not found at $NGINX_SITE; skipping."
fi

echo "Done."
