#!/bin/bash
echo "============================================"
echo "  MACHINE 3 — Webserver Nginx"
echo "============================================"

echo "[Machine 3] Attente des certificats..."
until [ -f "/shared/pki/.certs_ready" ]; do
    echo "  ... certificats pas encore prêts"
    sleep 3
done

echo "[Machine 3] Certificats OK — Démarrage Nginx..."
exec nginx -g "daemon off;"