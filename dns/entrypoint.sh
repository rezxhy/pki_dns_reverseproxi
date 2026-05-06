#!/bin/bash
# Machine 4 — bind9 + DNSSEC
set -e

KEY_DIR="/etc/bind/keys"
ZONE_DIR="/etc/bind/zones"
ZONE="home.arpa"

echo "============================================"
echo "  MACHINE 4 — DNS bind9 + DNSSEC"
echo "  Zone : home.arpa → jeu-2002.home.arpa"
echo "============================================"

# ── Création des dossiers ──
mkdir -p "$KEY_DIR" "$ZONE_DIR" /var/cache/bind
chown -R root:bind "$KEY_DIR" "$ZONE_DIR" /var/cache/bind
chmod -R 775 "$KEY_DIR" "$ZONE_DIR" /var/cache/bind

# ── Copie de la zone ──
cp /config/home.arpa.zone "$ZONE_DIR/home.arpa.zone"
chmod 664 "$ZONE_DIR/home.arpa.zone"

# ── Génération des clés DNSSEC ──
echo ""
echo "[Machine 4] Génération des clés DNSSEC..."
cd "$ZONE_DIR"

# Génère KSK et ZSK directement dans ZONE_DIR
dnssec-keygen -a RSASHA256 -b 2048 -f KSK -n ZONE -K "$ZONE_DIR" "$ZONE"
dnssec-keygen -a RSASHA256 -b 1024        -n ZONE -K "$ZONE_DIR" "$ZONE"

echo ""
echo "  ── Clés générées ──"
ls "$ZONE_DIR"/K*.key

# ── Signature de la zone ──
echo ""
echo "[Machine 4] Signature de la zone..."
cd "$ZONE_DIR"

echo "" >> "$ZONE_DIR/home.arpa.zone"
for key in "$ZONE_DIR"/K${ZONE}.*.key; do
    echo "\$INCLUDE $key" >> "$ZONE_DIR/home.arpa.zone"
done
echo "  [✓] Clés ajoutées dans la zone"

dnssec-signzone \
    -A \
    -3 $(openssl rand -hex 8) \
    -N INCREMENT \
    -o "$ZONE" \
    -f "$ZONE_DIR/home.arpa.zone.signed" \
    "$ZONE_DIR/home.arpa.zone" \
    $ZONE_DIR/K${ZONE}.*.key

echo "  [✓] Zone signée"
ls -la "$ZONE_DIR/"

# ── Mise à jour named.conf ──
sed -i 's|home.arpa.zone\"|home.arpa.zone.signed\"|g' /etc/bind/named.conf
echo "  [✓] named.conf mis à jour → $(grep file /etc/bind/named.conf)"

# ── Vérification ──
echo ""
named-checkconf && echo "  [✓] named.conf OK"

# ── Démarrage bind9 ──
echo ""
echo "[Machine 4] ✅ Démarrage bind9..."
exec named -g -c /etc/bind/named.conf -u root
