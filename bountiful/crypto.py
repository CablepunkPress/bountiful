"""Ed25519 key generation, signing, and verification."""

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
import base64


def generate_keypair() -> tuple[str, str]:
    """Generate an Ed25519 keypair.
    
    Returns (public_key_b64, private_key_b64) as base64-encoded strings
    for storage in SQLite.
    """
    private_key = Ed25519PrivateKey.generate()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    return (
        base64.b64encode(public_bytes).decode(),
        base64.b64encode(private_bytes).decode(),
    )


def sign(body: bytes, private_key_b64: str) -> str:
    """Sign a message body with a private key.
    
    Returns the signature as a base64-encoded string
    for use in an HTTP header.
    """
    private_bytes = base64.b64decode(private_key_b64)
    private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
    signature = private_key.sign(body)
    return base64.b64encode(signature).decode()


def verify(body: bytes, signature_b64: str, public_key_b64: str) -> bool:
    """Verify a signature against a public key.
    
    Returns True if valid, False if not.
    """
    try:
        public_bytes = base64.b64decode(public_key_b64)
        public_key = Ed25519PublicKey.from_public_bytes(public_bytes)
        signature = base64.b64decode(signature_b64)
        public_key.verify(signature, body)
        return True
    except Exception:
        return False