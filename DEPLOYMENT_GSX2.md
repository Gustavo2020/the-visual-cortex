# Despliegue de The Visual Cortex en gsx-2.com/the-visual-cortex

## Resumen
La aplicación Visual Cortex está desplegada bajo el subpath `/the-visual-cortex/` en el dominio gsx-2.com, detrás de Cloudflare Tunnel con proxy naranja activado.

## Arquitectura
```
Internet → Cloudflare (HTTPS) → Cloudflare Tunnel → Nginx (HTTP:80) → Docker Containers
                                                      ↓
                                                      ├─ API (127.0.0.1:8000)
                                                      └─ UI  (127.0.0.1:8501)
```

## Servicios

### API (Backend)
- **Puerto**: 127.0.0.1:8000
- **Container**: visual-cortex-api
- **Estado**: Healthy
- **Health check**: `curl http://127.0.0.1:8000/health`

### UI (Frontend Streamlit)
- **Puerto**: 127.0.0.1:8501
- **Container**: visual-cortex-ui
- **Ruta base**: `/the-visual-cortex`
- **Health check**: `curl http://127.0.0.1:8501/the-visual-cortex/`

## Configuración Nginx (Origin)

### Archivo
`/etc/nginx/sites-available/gsx-2.com`

### Bloques relevantes
```nginx
# Redirect sin trailing slash
location = /the-visual-cortex {
  return 301 https://$host/the-visual-cortex/;
}

# Proxy a Streamlit UI
location /the-visual-cortex/ {
  proxy_pass http://127.0.0.1:8501$request_uri;
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
```

## Comandos de Gestión

### Iniciar servicios
```bash
cd ~/the-visual-cortex
docker compose -f docker-compose.production.yml up -d api ui
```

### Parar servicios
```bash
docker compose -f docker-compose.production.yml down api ui
```

### Ver logs
```bash
# API
docker logs --tail=50 -f visual-cortex-api

# UI
docker logs --tail=50 -f visual-cortex-ui
```

### Rebuild después de cambios
```bash
cd ~/the-visual-cortex

# Rebuild API
docker compose -f docker-compose.production.yml build api
docker compose -f docker-compose.production.yml up -d api

# Rebuild UI
docker compose -f docker-compose.production.yml build ui
docker compose -f docker-compose.production.yml up -d ui
```

### Recargar Nginx
```bash
# Validar configuración
sudo nginx -t

# Recargar sin downtime
sudo systemctl reload nginx

# Reiniciar si es necesario
sudo systemctl restart nginx
```

### Verificar estado
```bash
# Contenedores
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep visual-cortex

# Health checks locales
curl http://127.0.0.1:8000/health
curl -I http://127.0.0.1:8501/the-visual-cortex/

# Via Nginx (local)
curl -I -H "Host: gsx-2.com" http://127.0.0.1/the-visual-cortex/

# Público (a través de Cloudflare)
curl -I https://gsx-2.com/the-visual-cortex/
```

## Configuración Cloudflare

### SSL/TLS
- **Modo**: Full (no strict) o Full Strict si tienes certs en el origin
- **Always Use HTTPS**: Habilitado
- **HTTP → HTTPS redirect**: Habilitado

### Network
- **WebSockets**: Habilitado (requerido para Streamlit)

### Caching
- **Page Rule para /the-visual-cortex/***: Bypass Cache (recomendado)
- Esto evita que Cloudflare cachee las respuestas dinámicas de Streamlit

### Tunnel
- Cloudflared activo en el servidor: `systemctl status cloudflared`
- Certificado: `~/.cloudflared/cert.pem`

## Variables de Entorno

### API Container
```
CLIP_MODEL=ViT-B-32
CLIP_PRETRAINED=openai
CLIP_DEVICE=cpu
EMBEDDINGS_DIR=/app/data/embeddings
LOG_LEVEL=INFO
```

### UI Container
```
API_HOST=api
API_PORT=8000
STREAMLIT_SERVER_PORT=8501
STREAMLIT_BASE_URL_PATH=the-visual-cortex
```

## Troubleshooting

### Página en blanco
1. Verificar que el contenedor UI esté healthy: `docker ps`
2. Ver logs: `docker logs visual-cortex-ui`
3. Verificar assets: `curl http://127.0.0.1:8501/the-visual-cortex/static/js/index.*.js`
4. Verificar en navegador: F12 → Network tab para ver errores 404

### 502 Bad Gateway
1. Verificar que los contenedores estén corriendo
2. Health check API: `curl http://127.0.0.1:8000/health`
3. Health check UI: `curl http://127.0.0.1:8501/the-visual-cortex/`
4. Ver logs de Nginx: `sudo tail -f /var/log/nginx/gsx-2.com.error.log`

### Assets 404
1. Verificar `STREAMLIT_BASE_URL_PATH` en docker-compose
2. Rebuild UI: `docker compose -f docker-compose.production.yml build ui && docker compose -f docker-compose.production.yml up -d ui`
3. Verificar proxy_pass en Nginx incluye `$request_uri`

### Sin espacio en disco
```bash
# Limpiar build cache
docker builder prune -af

# Limpiar imágenes no usadas
docker image prune -af

# Ver uso de disco
docker system df
df -h /
```

## URLs

- **Producción**: https://gsx-2.com/the-visual-cortex/
- **API Health**: https://gsx-2.com/the-visual-cortex/ (proxy interno, no expuesto públicamente)
- **Local UI**: http://127.0.0.1:8501/the-visual-cortex/
- **Local API**: http://127.0.0.1:8000/

## Archivos Clave

- **Nginx config**: `/etc/nginx/sites-available/gsx-2.com`
- **Docker Compose**: `~/the-visual-cortex/docker-compose.production.yml`
- **UI Dockerfile**: `~/the-visual-cortex/ui/Dockerfile`
- **API code**: `~/the-visual-cortex/src/api.py`
- **UI code**: `~/the-visual-cortex/ui/app.py`
- **Embeddings**: `~/the-visual-cortex/data/embeddings/`

## Notas

- El origin (Nginx) solo escucha HTTP:80; Cloudflare Tunnel maneja el HTTPS
- Los contenedores solo publican en 127.0.0.1 (localhost) por seguridad
- Streamlit requiere WebSockets; asegurar que Upgrade headers estén en Nginx
- La UI usa `--server.baseUrlPath=/the-visual-cortex` para servir bajo subpath
