"""
MACHINE 1 — Root CA
====================
Rôle : Créer la CA racine auto-signée et signer les 2 CA filles

Fichiers produits :
  /shared/pki/root_ca.key  → clé privée Root CA
  /shared/pki/root_ca.crt  → certificat Root CA (auto-signé)
  /shared/pki/int_ca_1.crt → certificat AC Fille 1 (signé par Root)
  /shared/pki/int_ca_2.crt → certificat AC Fille 2 (signé par Root)
"""

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timezone, timedelta
import os, time

PKI = "/shared/pki"
os.makedirs(PKI, exist_ok=True)

# ── Utilitaires ────────────────────────────────────────────────

def gen_key(bits=4096):
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

def wait(path, timeout=180):
    for _ in range(timeout // 3):
        if os.path.exists(path):
            return
        print(f"  ... attente : {path}")
        time.sleep(3)
    raise TimeoutError(f"Fichier jamais apparu : {path}")

# ── Étape 1 : Créer la Root CA ─────────────────────────────────

def create_root_ca():
    """Crée une CA racine auto-signée (subject == issuer)."""
    print("\n[1/3] Création Root CA...")

    key = gen_key(4096)

    name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,      "FR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PKI-Projet"),
        x509.NameAttribute(NameOID.COMMON_NAME,       "Root CA"),
    ])

    crt = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)                           # auto-signé
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))  # 10 ans
        # CA=True, path_length=1 → peut signer 1 niveau de sous-CA
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=True, key_cert_sign=True, crl_sign=True,
            content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False,
            encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256(), default_backend())  # signée par elle-même
    )

    save_key(key, f"{PKI}/root_ca.key")
    save_crt(crt, f"{PKI}/root_ca.crt")
    print("  [✓] Root CA créée (auto-signée, 10 ans)")
    return key, crt

# ── Étape 2 : Signer les CSR des AC filles ─────────────────────

def sign_intermediate(root_key, root_crt, index):
    """
    Attend le CSR d'une AC fille, le signe avec la Root CA,
    et produit le certificat de l'AC fille.
    """
    print(f"\n[{index+1}/3] Signature AC Fille {index}...")

    csr_path = f"{PKI}/int_ca_{index}.csr"
    wait(csr_path)

    with open(csr_path, "rb") as f:
        csr = x509.load_pem_x509_csr(f.read(), default_backend())

    crt = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(root_crt.subject)               # émetteur = Root CA
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1825))  # 5 ans
        # CA=True, path_length=0 → ne peut pas signer d'autres CA
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=True, key_cert_sign=True, crl_sign=True,
            content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False,
            encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(csr.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()), critical=False)
        .sign(root_key, hashes.SHA256(), default_backend())  # signée par Root CA
    )

    save_crt(crt, f"{PKI}/int_ca_{index}.crt")
    print(f"  [✓] AC Fille {index} signée par Root CA (5 ans)")


# ── Main ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  MACHINE 1 — Root CA")
    print("=" * 50)

    # Ne pas régénérer si déjà fait
    if os.path.exists(f"{PKI}/root_ca.crt"):
        print("✅ Root CA déjà existante — pas de régénération.")
        open(f"{PKI}/.root_done", "w").close()
        exit(0)

    root_key, root_crt = create_root_ca()
    sign_intermediate(root_key, root_crt, 1)
    sign_intermediate(root_key, root_crt, 2)

    open(f"{PKI}/.root_done", "w").close()
    print("\n✅ Machine 1 terminée.")
