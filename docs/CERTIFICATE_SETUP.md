# Certificate Management Configuration

## Let's Encrypt Auto-Renewal Script

```bash
#!/bin/bash
# /usr/local/bin/renew-clip-certs.sh

set -e

DOMAIN="your-domain.com"
CERT_DIR="/home/your-user/the-visual-cortex/certs"
DOCKER_DIR="/home/your-user/the-visual-cortex"
LOG_FILE="/var/log/clip-search/certbot.log"

echo "$(date): Starting certificate renewal..." >> $LOG_FILE

# Renew certificate
certbot renew --quiet --agree-tos 2>> $LOG_FILE

# Copy certificates if renewed
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $CERT_DIR/
    cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $CERT_DIR/
    cp /etc/letsencrypt/live/$DOMAIN/chain.pem $CERT_DIR/
    
    # Set permissions
    chmod 644 $CERT_DIR/fullchain.pem
    chmod 600 $CERT_DIR/privkey.pem
    chmod 644 $CERT_DIR/chain.pem
    
    # Reload services
    echo "$(date): Reloading Nginx..." >> $LOG_FILE
    
    # For Docker
    cd $DOCKER_DIR
    docker-compose -f docker-compose.production.yml exec -T nginx nginx -s reload
    
    # For Systemd
    # sudo systemctl reload nginx
    
    echo "$(date): Certificate renewal completed." >> $LOG_FILE
else
    echo "$(date): No certificate found at expected path." >> $LOG_FILE
fi
```

## Crontab Entry

```bash
# Run renewal every day at 2 AM
0 2 * * * /usr/local/bin/renew-clip-certs.sh
```

## One-Time Setup

```bash
#!/bin/bash
# Initial certificate setup

DOMAIN="your-domain.com"
CERT_DIR="./certs"

# Create directory
mkdir -p $CERT_DIR

# Option 1: Let's Encrypt (Production)
echo "Using Let's Encrypt for $DOMAIN"
sudo certbot certonly --standalone -d $DOMAIN -d www.$DOMAIN

# Option 2: Self-signed (Testing only)
# openssl req -x509 -newkey rsa:4096 \
#   -keyout $CERT_DIR/privkey.pem \
#   -out $CERT_DIR/fullchain.pem \
#   -days 365 -nodes

# Copy to local directory
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $CERT_DIR/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $CERT_DIR/
sudo cp /etc/letsencrypt/live/$DOMAIN/chain.pem $CERT_DIR/

# Set permissions
sudo chown -R $USER:$USER $CERT_DIR/
chmod 644 $CERT_DIR/fullchain.pem
chmod 600 $CERT_DIR/privkey.pem
chmod 644 $CERT_DIR/chain.pem

echo "Certificates installed in $CERT_DIR"
```
