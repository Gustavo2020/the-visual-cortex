# 🌐 Recomendaciones para Despliegue HTTPS con FastAPI

## 📋 Resumen Ejecutivo

Para desplegar **the-visual-cortex en HTTPS**, recomiendo esta **arquitectura en 3 capas**:

```
🔒 HTTPS (Port 443)
        ↓
    [Nginx]  ← Reverse Proxy, SSL/TLS, Rate Limiting
        ↓
    HTTP (Port 8000)
        ↓
 [Gunicorn] ← 4-8 workers (Uvicorn)
        ↓
 [FastAPI] ← api.py - Lógica de negocio
```

---

## ✅ Mi Recomendación (Ranked)

### 🥇 OPCIÓN 1: Docker Compose + Let's Encrypt (RECOMENDADO)

**Pros:**
- ✅ Más simple de desplegar
- ✅ Auto-renovación de certificados integrada
- ✅ Scaling automático
- ✅ Entorno reproducible
- ✅ Fácil rollback

**Pasos:**

```bash
# 1. Generar certificados Let's Encrypt
sudo certbot certonly --standalone -d tu-dominio.com

# 2. Copiar certificados
mkdir certs
sudo cp /etc/letsencrypt/live/tu-dominio.com/fullchain.pem certs/
sudo cp /etc/letsencrypt/live/tu-dominio.com/privkey.pem certs/

# 3. Actualizar nginx.conf con tu dominio
# Editar src/nginx.conf - línea 87:
# server_name tu-dominio.com www.tu-dominio.com;

# 4. Desplegar
docker-compose -f docker-compose.production.yml up -d

# 5. Verificar
curl https://tu-dominio.com/health
```

**Estructura:**
```
the-visual-cortex/
├── certs/
│   ├── fullchain.pem
│   └── privkey.pem
├── data/embeddings/
├── logs/
├── src/
│   ├── api.py
│   ├── search.py
│   ├── nginx.conf         ← Configurar aquí tu dominio
│   └── Dockerfile
└── docker-compose.production.yml  ← Desplegar con este
```

---

### 🥈 OPCIÓN 2: Servidor Linux + Systemd + Certbot

**Pros:**
- ✅ Control total del sistema
- ✅ Menos overhead que Docker
- ✅ Fácil integración con herramientas existentes
- ✅ Certificados auto-renovábles

**Pasos:**

```bash
# 1. Instalar dependencias
sudo apt-get update
sudo apt-get install -y python3 python3-venv nginx certbot

# 2. Setup aplicación
git clone <repo>
cd the-visual-cortex/src
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# 3. Generar certificados
sudo certbot certonly --standalone -d tu-dominio.com

# 4. Configurar Nginx
sudo cp src/nginx.conf /etc/nginx/nginx.conf
# Editar /etc/nginx/nginx.conf con tu dominio

# 5. Configurar Systemd
sudo cp src/clip-search-api.service /etc/systemd/system/
# Editar las rutas en /etc/systemd/system/clip-search-api.service
sudo systemctl daemon-reload
sudo systemctl start clip-search-api
sudo systemctl enable clip-search-api

# 6. Iniciar Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# 7. Verificar
curl https://tu-dominio.com/health
```

**Ventaja:**
- Menor consumo de memoria
- Mejor rendimiento
- Control fino de workers

---

### 🥉 OPCIÓN 3: Kubernetes (Para Scale-Out)

**Si necesitas:**
- Auto-scaling automático
- Multi-región
- Load balancing avanzado
- Clustering

Ver: [Kubernetes Deployment](./KUBERNETES_DEPLOYMENT.md)

---

## 🔧 Archivos Creados para ti

He creado los siguientes archivos de configuración:

### 1. **nginx.conf** (346 líneas)
```
✅ SSL/TLS configurado
✅ Rate limiting por endpoint
✅ Security headers (HSTS, CSP, etc.)
✅ Upstream workers
✅ Redirección HTTP → HTTPS
✅ Gzip compression
✅ CORS ready
```

### 2. **docker-compose.production.yml**
```
✅ Nginx reverse proxy
✅ FastAPI backend
✅ Volumes para embeddings
✅ Health checks
✅ Logging centralizado
✅ Resource limits
✅ Network isolation
```

### 3. **deploy-production.sh**
```
✅ Script de despliegue automático
✅ Validación de certificados
✅ Gunicorn con múltiples workers
✅ Logs configurados
```

### 4. **clip-search-api.service**
```
✅ Servicio Systemd
✅ Auto-start en reboot
✅ Logs con journalctl
✅ Restart automático
```

### 5. **HTTPS_DEPLOYMENT_GUIDE.md** (Guía Completa)
```
✅ Instrucciones paso a paso
✅ Let's Encrypt setup
✅ Auto-renovación
✅ Testing y troubleshooting
✅ Security checklist
```

---

## 🚀 Ruta Rápida (5 minutos)

```bash
# 1. Ir al directorio
cd /home/arcanegus/the-visual-cortex

# 2. Generar certificados (reemplaza tu-dominio.com)
sudo certbot certonly --standalone -d tu-dominio.com

# 3. Copiar certs
mkdir -p certs
sudo cp /etc/letsencrypt/live/tu-dominio.com/fullchain.pem certs/
sudo cp /etc/letsencrypt/live/tu-dominio.com/privkey.pem certs/
sudo chown -R $USER:$USER certs/

# 4. Editar nginx.conf
sed -i 's/your-domain.com/tu-dominio.com/g' src/nginx.conf

# 5. Desplegar
docker-compose -f src/docker-compose.production.yml up -d

# 6. Verificar
sleep 5
curl https://tu-dominio.com/health

# 7. Ver documentación API
# Abrir en navegador: https://tu-dominio.com/docs
```

---

## 🔒 Seguridad Configurada

✅ **SSL/TLS**
- TLS 1.2 + 1.3
- Ciphers fuertes
- OCSP Stapling

✅ **Headers de Seguridad**
- HSTS (Strict Transport Security)
- CSP (Content Security Policy)
- X-Frame-Options (SAMEORIGIN)
- X-Content-Type-Options (nosniff)
- X-XSS-Protection

✅ **Rate Limiting**
- General: 30 req/s
- Search: 10 req/s
- Health: 60 req/s
- Customizable por endpoint

✅ **HTTP → HTTPS Redirect**
- Automatizado en nginx

✅ **Validación de Entrada**
- Ya implementado en FastAPI

---

## 📊 Rendimiento Esperado

### Con CPU (ViT-B-32)
- Latencia: 100-150ms por búsqueda
- Throughput: 20-40 req/s con Nginx

### Con GPU (NVIDIA RTX)
- Latencia: 5-15ms por búsqueda
- Throughput: 100+ req/s

### Configuración para 1000 req/s
```nginx
worker_processes 8;
worker_connections 4096;

upstream clip_api {
    least_conn;  # Balance por conexión
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}
```

---

## 🛠️ Monitoreo Recomendado

```bash
# Logs en tiempo real
docker-compose -f docker-compose.production.yml logs -f nginx

# Métricas del sistema
docker stats

# SSL Check
openssl s_client -connect tu-dominio.com:443

# SSL Rating (A+ = Excelente)
# https://www.ssllabs.com/ssltest/analyze.html?d=tu-dominio.com

# Uptime monitoring
# Usar: updown.io, StatusPage, etc.
```

---

## 🔄 Auto-Renovación de Certificados

Automática con:
- Let's Encrypt (90 días validez)
- Renewal automático a los 60 días
- Script en `CERTIFICATE_SETUP.md`

```bash
# Verificar certificados
sudo certbot certificates

# Renovar manualmente
sudo certbot renew

# Automático vía cron:
0 2 * * * /usr/local/bin/renew-clip-certs.sh
```

---

## 📋 Checklist Pre-Despliegue

- [ ] Dominio apuntando a servidor
- [ ] Puerto 80 y 443 abiertos
- [ ] Certificados generados (Let's Encrypt)
- [ ] nginx.conf actualizado con tu dominio
- [ ] .env configurado
- [ ] Data/embeddings disponibles
- [ ] Docker/docker-compose instalado
- [ ] Espacio en disco suficiente (4GB+ recomendado)

---

## 🎯 Próximos Pasos

1. **Elige opción:**
   - Docker (RECOMENDADO) → Ve a Docker Compose
   - Linux → Ve a Systemd setup

2. **Lee la guía:**
   - `HTTPS_DEPLOYMENT_GUIDE.md`

3. **Configura:**
   - Sustituye `tu-dominio.com` en archivos

4. **Despliega:**
   - Ejecuta `docker-compose.production.yml` o servicio systemd

5. **Verifica:**
   - `curl https://tu-dominio.com/health`
   - Abre `https://tu-dominio.com/docs` en navegador

---

## 📚 Archivos Nuevos

```
src/
├── nginx.conf                          ← Configuración Nginx (HTTPS, Rate Limit)
├── docker-compose.production.yml       ← Production stack completo
├── deploy-production.sh                ← Script de despliegue
├── clip-search-api.service             ← Servicio Systemd
├── HTTPS_DEPLOYMENT_GUIDE.md           ← Guía paso a paso
└── CERTIFICATE_SETUP.md                ← Gestión de certificados
```

---

## 🎉 ¡Listo!

Con esta configuración tendrás:

✅ **the-visual-cortex corriendo en HTTPS**  
✅ **FastAPI con múltiples workers**  
✅ **Nginx como reverse proxy**  
✅ **Rate limiting automático**  
✅ **Certificados auto-renovables**  
✅ **Logging centralizado**  
✅ **Health checks**  
✅ **Escalable (fácil agregar más workers)**  

¿Preguntas o necesitas ajustes? 🚀
