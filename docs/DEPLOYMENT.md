# Production Deployment Guide for The Visual Cortex

This guide walks you through deploying The Visual Cortex semantic image search system to a production server with SSL/HTTPS support.

## Prerequisites

- A Linux server (Ubuntu 20.04 LTS or newer recommended)
- Root or sudo access
- A domain name pointing to your server
- ~5GB disk space (for images and embeddings)
- Docker and Docker Compose installed

### Install Docker and Docker Compose

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose (included in Docker Desktop, or install separately)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

## Step 1: Clone and Prepare Repository

```bash
# Clone the repository
git clone <your-repo-url> /opt/visual-cortex
cd /opt/visual-cortex

# Create necessary directories
mkdir -p certs logs data/embeddings data/images

# Create .env file from template
cp .env.example .env

# Edit .env with your configuration
nano .env
# Update:
#   - DOMAIN=yourdomain.com
#   - CLIP_MODEL (default: openai for ViT-B-32)
#   - API_HOST=api (internal Docker network)
#   - API_PORT=8000
```

## Step 2: Prepare Embeddings (First Time Only)

If you don't have pre-computed embeddings:

```bash
# Download and process images (from COCO dataset)
python src/embed_images.py

# This creates:
#   - data/embeddings/image_embeddings.npy
#   - data/embeddings/image_filenames.npy
#   - data/embeddings/metadata.json
```

If you already have images but no embeddings:

```bash
# Generate embeddings from existing images
python src/embed_images.py
```

## Step 3: Configure SSL Certificates

### Option A: Using Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt-get install -y certbot

# Stop any web servers that might block port 80
sudo systemctl stop apache2 2>/dev/null || true
sudo systemctl stop nginx 2>/dev/null || true

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates to your project
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./certs/

# Fix permissions
sudo chown $USER:$USER certs/*
chmod 644 certs/fullchain.pem
chmod 600 certs/privkey.pem
```

### Option B: Self-Signed Certificate (For Testing Only)

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes -out certs/fullchain.pem -keyout certs/privkey.pem -days 365

# This will prompt for certificate details - fill them in or press Enter
```

### Set Up Automatic Certificate Renewal

```bash
# Create renewal script
cat > renew-certs.sh << 'EOF'
#!/bin/bash
certbot renew --quiet
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./certs/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./certs/
docker-compose -f docker-compose.production.yml restart nginx
EOF

chmod +x renew-certs.sh

# Add to crontab for automatic renewal (30 days before expiry)
(crontab -l 2>/dev/null | grep -v "renew-certs.sh"; echo "0 3 * * * /opt/visual-cortex/renew-certs.sh") | crontab -
```

## Step 4: Build and Start Services

```bash
# Make deployment script executable
chmod +x deploy-production.sh

# Run deployment script
./deploy-production.sh yourdomain.com

# Or deploy manually:
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d

# Verify services are running
docker-compose -f docker-compose.production.yml ps
```

## Step 5: Verify Deployment

### Test API Health

```bash
# Wait 10-30 seconds for services to fully start, then:

# Check API health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"2025-12-24T..."}

# Test search endpoint
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "dog in park", "top_k": 5}'

# Expected response: JSON with results array
```

### Test UI Access

```bash
# From your local machine:
curl -I https://yourdomain.com/

# Expected: HTTP/1.1 200 OK
# Also check: https://yourdomain.com (should load Streamlit UI)
```

### Check Logs

```bash
# View all service logs
docker-compose -f docker-compose.production.yml logs -f

# View specific service logs
docker-compose -f docker-compose.production.yml logs -f api
docker-compose -f docker-compose.production.yml logs -f ui
docker-compose -f docker-compose.production.yml logs -f nginx
```

## Step 6: Configure DNS and Firewall

### Update DNS Records

Point your domain to your server:

```
A     yourdomain.com     <your-server-ip>
AAAA  yourdomain.com     <your-server-ipv6>  (if IPv6 available)
A     www.yourdomain.com <your-server-ip>
```

DNS propagation typically takes 24-48 hours.

### Configure Firewall

```bash
# If using UFW
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable

# Verify rules
sudo ufw status
```

## Step 7: Monitor and Maintain

### Regular Health Checks

```bash
# Check all services are healthy
docker-compose -f docker-compose.production.yml ps

# Monitor resource usage
docker stats

# Check disk usage
df -h data/
```

### View Logs

```bash
# Real-time logs (all services)
docker-compose -f docker-compose.production.yml logs -f

# Last 100 lines from API
docker-compose -f docker-compose.production.yml logs --tail=100 api

# Export logs
docker-compose -f docker-compose.production.yml logs > deployment.log
```

### Update Configuration

To update settings without redeploying:

```bash
# Edit .env
nano .env

# Restart affected services
docker-compose -f docker-compose.production.yml restart api
docker-compose -f docker-compose.production.yml restart ui

# Verify health
docker-compose -f docker-compose.production.yml ps
```

### Restart Services

```bash
# Graceful restart (preserves data)
docker-compose -f docker-compose.production.yml restart

# Full redeploy (preserves volumes)
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d
```

### Backup Data

```bash
# Backup embeddings
tar -czf embeddings-backup-$(date +%Y%m%d).tar.gz data/embeddings/

# Backup configuration
cp .env .env.backup.$(date +%Y%m%d)
cp docker-compose.production.yml docker-compose.backup.$(date +%Y%m%d).yml
```

## Troubleshooting

### Issue: Services Won't Start

```bash
# Check logs for errors
docker-compose -f docker-compose.production.yml logs api

# Common causes:
# 1. Port already in use: sudo lsof -i :8000
# 2. Missing embeddings: python src/embed_images.py
# 3. Permission issues: sudo chown -R $USER:$USER .

# Solution: stop and restart
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d
```

### Issue: API Returns 502 Bad Gateway

```bash
# API might still be starting (takes 1-2 minutes)
# Wait and retry, or check logs:
docker-compose -f docker-compose.production.yml logs api

# Manually restart API
docker-compose -f docker-compose.production.yml restart api
```

### Issue: SSL Certificate Errors

```bash
# Verify certificate validity
openssl x509 -in certs/fullchain.pem -text -noout | grep -A 2 "Validity"

# If expired, renew:
sudo certbot renew
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./certs/

# Restart Nginx
docker-compose -f docker-compose.production.yml restart nginx
```

### Issue: High Memory Usage

```bash
# Check which container is consuming memory
docker stats

# Reduce resource limits in docker-compose.production.yml:
# limits:
#   memory: 2G  # Reduce from 4G

docker-compose -f docker-compose.production.yml up -d --no-deps api
```

### Issue: Database/Embeddings Corruption

```bash
# Verify embeddings file integrity
python -c "
import numpy as np
emb = np.load('data/embeddings/image_embeddings.npy')
names = np.load('data/embeddings/image_filenames.npy')
print(f'Embeddings shape: {emb.shape}')
print(f'Filenames count: {len(names)}')
assert emb.shape[0] == len(names), 'Mismatch!'
print('✓ Embeddings file is valid')
"

# If corrupted, regenerate:
rm -rf data/embeddings/*
python src/embed_images.py
```

## Performance Optimization

### Model Selection

The default model is `ViT-B-32 (openai)` - good balance of speed and accuracy on CPU.

For GPU servers (if available):
```bash
# Update .env
CLIP_MODEL=ViT-SO400M-14-SigLIP-384
CLIP_DEVICE=cuda
CLIP_PRETRAINED=webli
```

For CPU-only (current setup):
```bash
# Already optimized, use default ViT-B-32
CLIP_DEVICE=cpu
```

### Caching

The system uses pre-computed embeddings, so initial requests are fast (~100ms).

### Database Optimization

Current implementation uses NumPy files (not a database). For 1000+ images, consider:
- **Vector databases**: Milvus, Weaviate, Qdrant
- **Search engines**: Elasticsearch with vector support
- **Cloud solutions**: Pinecone, Supabase Vector

## Scaling for More Images

To add more images to your existing deployment:

```bash
# 1. Copy new images to data/images/
cp /path/to/new/images/*.jpg data/images/

# 2. Generate embeddings for all images
python src/embed_images.py

# 3. Restart API to load new embeddings
docker-compose -f docker-compose.production.yml restart api

# 4. Verify health
curl http://localhost:8000/health
```

## Production Checklist

- [ ] Domain name configured and pointing to server
- [ ] SSL certificates obtained from Let's Encrypt
- [ ] .env file customized with your settings
- [ ] Embeddings generated from your image dataset
- [ ] Firewall configured (ports 80, 443 open)
- [ ] Docker and Docker Compose installed
- [ ] Services verified healthy
- [ ] DNS propagation completed
- [ ] Automatic certificate renewal configured
- [ ] Backup strategy implemented

## Support

For issues or questions:

1. Check [DEPLOYMENT.md](docs/DEPLOYMENT.md) (this file)
2. Review logs: `docker-compose -f docker-compose.production.yml logs -f`
3. Check system resources: `docker stats`
4. Verify configuration: `cat .env`

## Security Notes

- **Certificates**: Let's Encrypt certificates are free and auto-renew
- **Firewall**: Only expose ports 80 (HTTP) and 443 (HTTPS)
- **Updates**: Regularly update Docker images:
  ```bash
  docker-compose pull
  docker-compose -f docker-compose.production.yml up -d
  ```
- **Backups**: Regular backups of `data/embeddings/` and `.env`
- **Monitoring**: Set up log monitoring and alerts for production use

---

**Last Updated:** 2025-12-24  
**Version:** 2.0 (Production Ready)  
**Status:** Ready for deployment
