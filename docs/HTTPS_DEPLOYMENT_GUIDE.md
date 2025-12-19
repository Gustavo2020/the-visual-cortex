# HTTPS Deployment Guide for CLIP Image Search

## 🔒 Opciones de Despliegue con HTTPS

### OPCIÓN 1: Docker Compose (RECOMENDADO - Más Simple)

#### Paso 1: Generar Certificados SSL

**Opción A: Let's Encrypt (Recomendado para Producción)**

```bash
# Instalar certbot
sudo apt-get install certbot python3-certbot-nginx

# Generar certificado
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Copiar certificados
mkdir -p certs
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem certs/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem certs/
sudo cp /etc/letsencrypt/live/your-domain.com/chain.pem certs/

# Permisos
sudo chown -R $USER:$USER certs/
chmod 600 certs/privkey.pem
```

**Opción B: Auto-firmado (Para Testing)**

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:4096 \
  -keyout certs/privkey.pem \
  -out certs/fullchain.pem \
  -days 365 -nodes \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"
```

#### Paso 2: Configurar Dominio en Nginx

Editar `src/nginx.conf` y reemplazar:
```bash
server_name your-domain.com www.your-domain.com;
```

#### Paso 3: Desplegar

```bash
# Construir imágenes
docker-compose -f docker-compose.production.yml build

# Iniciar servicios
docker-compose -f docker-compose.production.yml up -d

# Verificar estado
docker-compose -f docker-compose.production.yml ps
docker-compose -f docker-compose.production.yml logs -f nginx
```

---

### OPCIÓN 2: Servidor Linux (Más Control)

#### Paso 1: Configuración del Sistema

```bash
# Actualizar sistema
sudo apt-get update && sudo apt-get upgrade -y

# Instalar dependencias
sudo apt-get install -y python3 python3-venv python3-pip \
  nginx certbot python3-certbot-nginx curl git

# Clonar repositorio
git clone https://github.com/your-org/the-visual-cortex.git
cd the-visual-cortex/src

# Crear virtualenv
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias Python
pip install -r requirements.txt
pip install gunicorn
```

#### Paso 2: Certificados SSL

```bash
# Generar certificado Let's Encrypt
sudo certbot certonly --standalone -d your-domain.com

# Crear directorio de certs
mkdir -p certs
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem certs/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem certs/
sudo chown -R $USER:$USER certs/
```

#### Paso 3: Configurar Nginx

```bash
# Copiar configuración
sudo cp src/nginx.conf /etc/nginx/nginx.conf

# Validar configuración
sudo nginx -t

# Iniciar Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

#### Paso 4: Configurar Servicio Systemd

```bash
# Copiar archivo de servicio
sudo cp src/clip-search-api.service /etc/systemd/system/

# Editar rutas en el archivo
sudo nano /etc/systemd/system/clip-search-api.service
# Reemplazar /path/to/the-visual-cortex por la ruta real

# Crear directorio de logs
sudo mkdir -p /var/log/clip-search
sudo chown www-data:www-data /var/log/clip-search

# Habilitar y iniciar servicio
sudo systemctl daemon-reload
sudo systemctl enable clip-search-api
sudo systemctl start clip-search-api

# Verificar estado
sudo systemctl status clip-search-api
```

#### Paso 5: Auto-renovación de Certificados

```bash
# Crear script de renovación
sudo nano /usr/local/bin/renew-clip-certs.sh
```

```bash
#!/bin/bash
certbot renew --quiet
# Recargar Nginx
systemctl reload nginx
```

```bash
# Hacer ejecutable
sudo chmod +x /usr/local/bin/renew-clip-certs.sh

# Agregar a crontab
sudo crontab -e
# Agregar línea:
0 2 * * * /usr/local/bin/renew-clip-certs.sh
```

---

## 🧪 Testing

### Verificar HTTPS

```bash
# Validar SSL
curl -I https://your-domain.com/health

# Verificar certificado
openssl s_client -connect your-domain.com:443

# Test con SSLLabs
# Visitar: https://www.ssllabs.com/ssltest/analyze.html?d=your-domain.com
```

### Verificar API

```bash
# Health check
curl https://your-domain.com/health

# Search API
curl -X POST https://your-domain.com/search \
  -H "Content-Type: application/json" \
  -d '{"query":"a red car","top_k":5}'

# Documentación API
curl https://your-domain.com/docs
```

---

## 📊 Monitoreo

### Logs

```bash
# Docker
docker-compose -f docker-compose.production.yml logs -f nginx
docker-compose -f docker-compose.production.yml logs -f clip-search-api

# Systemd
sudo journalctl -u clip-search-api -f
sudo tail -f /var/log/nginx/error.log
```

### Métricas

```bash
# Ver uso de recursos
docker stats

# Monitoreo del sistema
top
htop  # Si está instalado
```

---

## 🔐 Security Checklist

- [ ] SSL/TLS configurado correctamente
- [ ] HSTS headers activados
- [ ] Rate limiting configurado en nginx
- [ ] Firewall configurado (UFW/IPTables)
- [ ] Auto-renovación de certificados activa
- [ ] Logs centralizados
- [ ] Backups de embeddings programados
- [ ] Monitoreo de uptime activo
- [ ] API authentication implementada
- [ ] CORS configurado apropiadamente

---

## 🚀 Performance Optimization

### Nginx

```bash
# Aumentar workers según CPU
worker_processes auto;

# Ajustar conexiones
worker_connections 2048;

# Gzip compression
gzip on;
gzip_comp_level 6;
```

### Gunicorn

```bash
# Aumentar workers (2-4 por core)
--workers 8

# Ajustar timeout
--timeout 120

# Keep-alive
--keep-alive 5
```

### FastAPI

```python
# En api.py, añadir middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware

app.add_middleware(GZIPMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## 🆘 Troubleshooting

### Certificado no se renueva

```bash
# Verificar servicio certbot
sudo systemctl status certbot.timer

# Renovar manualmente
sudo certbot renew --force-renewal

# Ver últimas renovaciones
sudo certbot certificates
```

### Nginx no inicia

```bash
# Validar configuración
sudo nginx -t

# Ver errores
sudo journalctl -u nginx -n 50
```

### API no responde

```bash
# Verificar servicio
sudo systemctl status clip-search-api

# Ver logs
sudo journalctl -u clip-search-api -f

# Reiniciar
sudo systemctl restart clip-search-api
```

### Rate limiting muy restrictivo

Ajustar en `nginx.conf`:
```nginx
limit_req_zone $binary_remote_addr zone=search_limit:10m rate=10r/s;
                                                              ^^^^^^
                                                        Aumentar aquí
```

---

## 📋 Arquitectura Final

```
┌─────────────────────┐
│   Cliente HTTPS     │
│ https://domain.com  │
└──────────┬──────────┘
           │
           ▼ (SSL/TLS - Puerto 443)
┌─────────────────────────────────────┐
│  Nginx Reverse Proxy                │
│  - Rate limiting                    │
│  - Compression (Gzip)               │
│  - Security headers                 │
│  - Load balancing (si multiples)    │
└──────────┬──────────────────────────┘
           │
           ▼ (HTTP - Puerto 8000)
┌─────────────────────────────────────┐
│  Gunicorn (4-8 workers)             │
│  - Uvicorn workers                  │
│  - Multi-process                    │
│  - Graceful restart                 │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  FastAPI Application                │
│  - Search endpoints                 │
│  - Health checks                    │
│  - Documentation (Swagger)          │
└─────────────────────────────────────┘
```

---

## 📚 Referencias

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/configure.html)
- [OWASP Security Headers](https://owasp.org/www-project-secure-headers/)
