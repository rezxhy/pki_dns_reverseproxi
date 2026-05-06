═══════════════════════════════════════════════════════════════
  PKI DOCKER — jeu-2002.home.arpa
  Root AC → 2 AC Filles → Certificat serveur + DNSSEC
═══════════════════════════════════════════════════════════════

── PRÉREQUIS ──────────────────────────────────────────────────

  - Docker + docker-compose installés
  - WSL2 (Ubuntu 22.04)
  - Firefox ou Brave

── STRUCTURE ──────────────────────────────────────────────────

  pki/
  ├── docker-compose.yml
  ├── root_ca/          → Machine 1 : Root CA
  ├── intermediate_ca/  → Machine 2 : AC Filles + cert serveur
  ├── webserver/        → Machine 3 : Nginx HTTPS
  └── dns/              → Machine 4 : bind9 + DNSSEC

── LANCEMENT ──────────────────────────────────────────────────

  1. Se placer dans le dossier :
     cd ~/pki

  2. Libérer le port 53 si nécessaire :
     sudo systemctl stop systemd-resolved
     sudo systemctl disable systemd-resolved

  3. Lancer les 4 machines :
     docker-compose up --build

  4. Vérifier que tout tourne :
     docker ps

── RÉSOLUTION DNS ─────────────────────────────────────────────

  Configurer resolv.conf pour utiliser le DNS Docker :
     sudo nano /etc/resolv.conf

  Contenu :
     nameserver 127.0.0.1
     nameserver 8.8.8.8

  ⚠️  Remettre 8.8.8.8 en premier si docker-compose up --build
      ne fonctionne plus (Docker a besoin d'internet pour les images)

── ACCÈS AU SITE ──────────────────────────────────────────────

  Depuis le navigateur :
     https://jeu-2002.home.arpa:8443

  ⚠️  Le navigateur affichera un avertissement de sécurité
      car le certificat est auto-signé (non reconnu publiquement).
      → Cliquer sur "Avancé" puis "Continuer quand même"

  Pour supprimer l'avertissement → voir section CERTIFICAT ci-dessous.

── VÉRIFICATION DNS + DNSSEC ──────────────────────────────────

  Résolution DNS simple :
     dig @127.0.0.1 -p 5454 jeu-2002.home.arpa A

  Résolution avec DNSSEC :
     dig @127.0.0.1 -p 5454 jeu-2002.home.arpa A +dnssec

  Résultat attendu :
     - status: NOERROR
     - ANSWER: jeu-2002.home.arpa → 127.0.0.1
     - RRSIG présent → DNSSEC actif ✅

── CERTIFICAT ─────────────────────────────────────────────────

  Pour que le navigateur fasse confiance au certificat,
  il faut importer la Root CA dans le navigateur.

  1. Récupérer le certificat Root CA :
     docker run --rm \
       -v pki_pki_shared:/shared/pki \
       -v ~/pki:/output \
       python:3.11-slim \
       cp /shared/pki/root_ca.crt /output/root_ca.crt

  2. Importer dans Firefox :
     → about:preferences#privacy
     → Afficher les certificats
     → Onglet Autorités → Importer
     → Sélectionner ~/pki/root_ca.crt
     → Cocher "Faire confiance pour identifier les sites web"
     → OK → Redémarrer Firefox

  3. Importer dans Brave/Chrome :
     brave://settings/certificates
     → Onglet Autorités → Importer
     → Sélectionner ~/pki/root_ca.crt
     → Cocher "Faire confiance pour identifier les sites web"

  ⚠️  À chaque docker-compose down -v les certificats sont
      régénérés → il faut réimporter la Root CA.
      Utiliser docker-compose down (sans -v) pour les conserver.

── CHAÎNE PKI ─────────────────────────────────────────────────

  Root CA (10 ans, auto-signée)
    └── Intermediate CA 1 (5 ans, signée par Root CA)
    │     └── server.crt (1 an, signé par Intermediate CA 1)
    └── Intermediate CA 2 (5 ans, signée par Root CA)

  Fichiers dans le volume Docker pki_pki_shared :
     root_ca.key / root_ca.crt
     int_ca_1.key / int_ca_1.crt
     int_ca_2.key / int_ca_2.crt
     server.key / server.crt
     server_fullchain.crt  ← utilisé par Nginx

── ARRÊT ──────────────────────────────────────────────────────

  Arrêt simple (conserve les certificats) :
     docker-compose down

  Arrêt + suppression des certificats :
     docker-compose down -v

═══════════════════════════════════════════════════════════════
