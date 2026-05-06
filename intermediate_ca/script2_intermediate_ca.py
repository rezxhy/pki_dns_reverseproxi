"""
MACHINE 2 — AC Filles + Certificat serveur
===========================================
Rôle :
  1. Générer les clés + CSR des 2 AC filles
  2. Attendre que Root CA les signe
  3. Signer le certificat final du serveur web avec AC Fille 1

Fichiers produits :
  /shared/pki/int_ca_1.key       → clé privée AC Fille 1
  /shared/pki/int_ca_1.csr       → CSR AC Fille 1 (envoyé à Root CA)
  /shared/pki/int_ca_2.key       → clé privée AC Fille 2
  /shared/pki/int_ca_2.csr       → CSR AC Fille 2 (envoyé à Root CA)
  /shared/pki/server.key         → clé privée du serveur web
  /shared/pki/server.crt         → certificat du serveur (signé par AC Fille 1)
  /shared/pki/server_fullchain.crt → chaîne complète (server + int1 + root)
"""

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timezone, timedelta
import os, time

PKI    = "/shared/pki"
DOMAIN = "jeu-2002.home.arpa"   # domaine principal

# ── Utilitaires ────────────────────────────────────────────────

def gen_key(bits=2048):
    return rsa.generate_private_key(65537, bits, default_backend())

def save_key(key, path):
    with open(path, "wb") as f:
        f.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()
        ))
    print(f"  [clé]  {path}")

def save_crt(crt, path):
    with open(path, "wb") as f:
        f.write(crt.public_bytes(serialization.Encoding.PEM))
    print(f"  [cert] {path}")

def load_key(path):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())

def load_crt(path):
    with open(path, "rb") as f:
        return x509.load_pem_x509_certificate(f.read(), default_backend())

def wait(path, timeout=180):
    for _ in range(timeout // 3):
        if os.path.exists(path):
            return
        print(f"  ... attente : {path}")
        time.sleep(3)
    raise TimeoutError(f"Fichier jamais apparu : {path}")

# ── Étape 1 : Générer clé + CSR pour une AC fille ──────────────

def create_intermediate_csr(index):
    """
    Génère une clé privée et un CSR pour l'AC fille.
    Le CSR sera signé par la Machine 1 (Root CA).
    """
    print(f"\n[{index}/4] Génération CSR AC Fille {index}...")

    key = gen_key(4096)

    name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,      "FR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PKI-Projet"),
        x509.NameAttribute(NameOID.COMMON_NAME,       f"Intermediate CA {index}"),
    ])

    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(name)
        .sign(key, hashes.SHA256(), default_backend())
    )

    save_key(key, f"{PKI}/int_ca_{index}.key")

    with open(f"{PKI}/int_ca_{index}.csr", "wb") as f:
        f.write(csr.public_bytes(serialization.Encoding.PEM))
    print(f"  [CSR]  {PKI}/int_ca_{index}.csr → envoyé à Root CA")
    print(f"  [✓] CSR AC Fille {index} prêt")
    return key

# ── Étape 2 : Signer le certificat serveur ─────────────────────

def sign_server_cert(int_key_1, domain):
    """
    Crée et signe le certificat final du serveur web.
    Signé par AC Fille 1.
    Inclut tous les domaines dans le SAN.
    """
    print(f"\n[3/4] Signature du certificat serveur pour {domain}...")

    wait(f"{PKI}/int_ca_1.crt")
    int_crt_1 = load_crt(f"{PKI}/int_ca_1.crt")

    server_key = gen_key(2048)

    name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,      "FR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PKI-Projet"),
        x509.NameAttribute(NameOID.COMMON_NAME,       domain),
    ])

    crt = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(int_crt_1.subject)              # émetteur = AC Fille 1
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))   # 1 an
        # CA=False → certificat feuille (pas une CA)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        # SAN → tous les domaines couverts
        .add_extension(x509.SubjectAlternativeName([
            x509.DNSName("jeu-2002.home.arpa"),
            x509.DNSName("www.jeu-2002.home.arpa"),
            x509.DNSName("localhost"),
        ]), critical=False)
        .add_extension(x509.KeyUsage(
            digital_signature=True, key_encipherment=True,
            content_commitment=False, data_encipherment=False,
            key_agreement=False, key_cert_sign=False,
            crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.SERVER_AUTH,
        ]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(int_key_1.public_key()), critical=False)
        .sign(int_key_1, hashes.SHA256(), default_backend())  # signé par AC Fille 1
    )

    save_key(server_key, f"{PKI}/server.key")
    save_crt(crt,        f"{PKI}/server.crt")

    # Chaîne complète : server.crt + int_ca_1.crt + root_ca.crt
    # Nginx en a besoin pour présenter toute la chaîne au navigateur
    print("\n[4/4] Construction de la chaîne complète...")
    chain = f"{PKI}/server_fullchain.crt"
    with open(chain, "wb") as out:
        for p in [f"{PKI}/server.crt", f"{PKI}/int_ca_1.crt", f"{PKI}/root_ca.crt"]:
            with open(p, "rb") as f:
                out.write(f.read())
    print(f"  [chaîne] {chain}")
    print("  [✓] Certificat serveur prêt")


# ── Main ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  MACHINE 2 — AC Filles + Certificat serveur")
    print("=" * 50)

    # Ne pas régénérer si déjà fait
    if os.path.exists(f"{PKI}/int_ca_1.crt"):
        print("✅ Certificats déjà existants — pas de régénération.")
        open(f"{PKI}/.certs_ready", "w").close()
        exit(0)

    # Attente que Root CA soit prête
    print("\n[Machine 2] Attente de la Root CA (Machine 1)...")
    wait(f"{PKI}/root_ca.crt")

    # Génération des CSR pour les 2 AC filles
    int_key_1 = create_intermediate_csr(1)
    int_key_2 = create_intermediate_csr(2)

    # Attente que Root CA ait signé les 2 AC filles
    wait(f"{PKI}/int_ca_2.crt")

    # Signature du certificat serveur par AC Fille 1
    sign_server_cert(int_key_1, DOMAIN)

    # Signal pour Machine 3 (Nginx) et Machine 4 (DNS)
    open(f"{PKI}/.certs_ready", "w").close()
    print("\n✅ Machine 2 terminée.")
