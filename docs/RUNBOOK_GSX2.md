# Visual Cortex Runbook (gsx-2.com)

This runbook documents how to operate and troubleshoot The Visual Cortex deployment published at:

- Public URL: https://gsx-2.com/the-visual-cortex/
- Origin server: Nginx (system service) behind Cloudflare Tunnel
- App services (Docker): `visual-cortex-api`, `visual-cortex-ui`

## Overview
- UI: Streamlit served under subpath `/the-visual-cortex`
- API: FastAPI on port 8000 (localhost-bound)
- Reverse proxy: Origin Nginx proxies `/the-visual-cortex/` to UI on 127.0.0.1:8501
- Cloudflare: terminates HTTPS and forwards to origin (HTTP). WebSockets enabled.

## One-time Setup (already applied)
- Compose binds:
  - API → 127.0.0.1:8000
  - UI → 127.0.0.1:8501 with base path
- Streamlit base path: `STREAMLIT_BASE_URL_PATH=the-visual-cortex`
- Nginx origin site: `/etc/nginx/sites-available/gsx-2.com` with priority prefix match for `/the-visual-cortex/`

## Start / Stop / Restart
From the repo root docs: docker-compose.production.yml

```bash
# Start API + UI only (recommended; origin Nginx handles 80/443)
docker compose -f docker-compose.production.yml up -d api ui

# Stop only UI
docker compose -f docker-compose.production.yml stop ui

# Restart API or UI
docker compose -f docker-compose.production.yml restart api
docker compose -f docker-compose.production.yml restart ui

# Rebuild UI (after config/code changes)
docker compose -f docker-compose.production.yml build ui
docker compose -f docker-compose.production.yml up -d ui
```

## Origin Nginx (Cloudflare in front)
Effective site config (HTTP only at origin, HTTPS at Cloudflare):

```nginx
# /etc/nginx/sites-available/gsx-2.com
server {
  listen 80;
  listen [::]:80;
  server_name gsx-2.com www.gsx-2.com;

  # Landing page (SPA)
  root /var/www/gsx-2.com;
  index index.html;

  # Logs
  access_log /var/log/nginx/gsx-2.com.access.log;
  error_log  /var/log/nginx/gsx-2.com.error.log;

  # Redirect without trailing slash
  location = /the-visual-cortex { return 301 https://$host/the-visual-cortex/; }

  # Priority prefix for Streamlit UI under subpath
  location ^~ /the-visual-cortex/ {
    proxy_pass http://127.0.0.1:8501$request_uri;  # preserve full URI
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
    proxy_connect_timeout 86400;
    proxy_send_timeout 86400;
    add_header Cache-Control "no-cache, no-store, must-revalidate" always;
  }

  # SPA routing for landing page
  location / { try_files $uri $uri/ /index.html; }

  # Cache static assets for the landing page (priority lower than ^~ above)
  location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
  }
}
```

Apply changes safely:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Cloudflare Settings
- SSL/TLS: Use “Full (strict)” if using Origin CA; otherwise “Full”.
- WebSockets: Enabled (required for Streamlit).
- Cache Rule (recommended): Bypass cache for `https://gsx-2.com/the-visual-cortex/*`.
- Always Use HTTPS: Can be enabled at Cloudflare; origin listens HTTP.

## Health Checks & Verification
```bash
# API health (origin host)
curl -sS http://127.0.0.1:8000/health | jq

# UI direct (origin host)
curl -I http://127.0.0.1:8501/the-visual-cortex/

# Via origin Nginx with Host header
curl -I -H "Host: gsx-2.com" http://127.0.0.1/the-visual-cortex/

# Static assets via proxy
curl -I -H "Host: gsx-2.com" \
  http://127.0.0.1/the-visual-cortex/static/js/index.3bHSf9gi.js
```

## Logs
```bash
# Docker containers
docker logs -f visual-cortex-api
docker logs -f visual-cortex-ui

# Nginx origin
sudo tail -f /var/log/nginx/gsx-2.com.access.log
sudo tail -f /var/log/nginx/gsx-2.com.error.log
```

## Updating Embeddings
```bash
# From repo root: add images to data/images/
python src/embed_images.py

# Restart API to reload embeddings
docker compose -f docker-compose.production.yml restart api
```

## Disk Space (Docker)
```bash
# Show Docker disk usage
docker system df

# Prune build cache (safe)
docker builder prune -af

# Remove unused images (safe if not tagged/used)
docker image prune -af
```

## Troubleshooting
- Blank page / missing JS/CSS under `/the-visual-cortex/`:
  - Ensure Nginx uses `location ^~ /the-visual-cortex/ { ... }` (the `^~` is critical).
  - Ensure `proxy_pass http://127.0.0.1:8501$request_uri;` is set to forward full paths.
  - Confirm UI container is started with base path:
    ```bash
    docker exec visual-cortex-ui env | grep STREAMLIT_BASE_URL_PATH
    # → the-visual-cortex
    ```

- 404 via proxy, but 200 direct on 8501:
  - Check Nginx error log for attempts to open `/var/www/gsx-2.com/...` paths; that means regex `location ~*` is taking precedence. Keep `^~` on the `/the-visual-cortex/` block.

- 502 Bad Gateway:
  - UI may be starting. Verify: `curl -I http://127.0.0.1:8501/the-visual-cortex/`
  - Check container: `docker ps`, `docker logs visual-cortex-ui`

- Cloudflare HTTPS only:
  - With Cloudflare Tunnel, origin runs HTTP only; SSL is terminated at Cloudflare. No 443 listener required on origin.
  - If serving 443 directly in future, configure a 443 server with Origin CA or Let’s Encrypt certs.

- Rebuild errors (no space left on device):
  - Run `docker builder prune -af` and `docker image prune -af`, then rebuild.

## Quick Reference
```bash
# Start services
docker compose -f docker-compose.production.yml up -d api ui

# Verify
curl -sS http://127.0.0.1:8000/health
curl -I -H "Host: gsx-2.com" http://127.0.0.1/the-visual-cortex/

# Reload Nginx
sudo nginx -t && sudo systemctl reload nginx

# Logs
docker logs -f visual-cortex-api
docker logs -f visual-cortex-ui
sudo tail -f /var/log/nginx/gsx-2.com.error.log
```