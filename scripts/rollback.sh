#!/usr/bin/env bash
set -euo pipefail

# Restore from backups created by backup_before_cleanup.sh
# - Restore latest data/cache tarball
# - Restore latest Nginx site config backup and reload Nginx

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
BACKUPS_DIR="$REPO_DIR/data/backups"
NGINX_SITE="/etc/nginx/sites-available/gsx-2.com"

# Restore cache
CACHE_TAR="$(ls -1 "$BACKUPS_DIR"/cache-*.tar.gz 2>/dev/null | tail -n 1 || true)"
if [ -n "${CACHE_TAR:-}" ]; then
  echo "Restoring cache from $CACHE_TAR..."
  tar -C "$REPO_DIR/data" -xzf "$CACHE_TAR"
  echo "Cache restored to $REPO_DIR/data/cache"
else
  echo "No cache backup found; skipping cache restore."
fi

# Restore Nginx config
LATEST_NGINX_BAK="$(ls -1 "$NGINX_SITE".bak-* 2>/dev/null | tail -n 1 || true)"
if [ -n "${LATEST_NGINX_BAK:-}" ]; then
  echo "Restoring Nginx site config from $LATEST_NGINX_BAK..."
  if sudo cp "$LATEST_NGINX_BAK" "$NGINX_SITE"; then
    if sudo nginx -t; then
      sudo systemctl reload nginx
      echo "Nginx reloaded."
    else
      echo "Nginx config test failed; please review $NGINX_SITE."
    fi
  else
    echo "Could not restore Nginx config without sudo. Run: sudo cp \"$LATEST_NGINX_BAK\" \"$NGINX_SITE\" && sudo nginx -t && sudo systemctl reload nginx"
  fi
else
  echo "No Nginx backup found; skipping Nginx restore."
fi

echo "Rollback completed."
