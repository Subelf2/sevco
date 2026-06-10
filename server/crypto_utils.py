import json
import base64
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

from config import PRIVATE_KEY_FILE
from config import PUBLIC_KEY_FILE


def generate_keys():
    if Path(PRIVATE_KEY_FILE).exists():
        return

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    public_key = private_key.public_key()

    with open(PRIVATE_KEY_FILE, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        )

    with open(PUBLIC_KEY_FILE, "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        )


def load_private_key():
    with open(PRIVATE_KEY_FILE, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(),
            password=None
        )


def load_public_key():
    with open(PUBLIC_KEY_FILE, "rb") as f:
        return serialization.load_pem_public_key(
            f.read()
        )


def sign_participation_token(data):
    private_key = load_private_key()

    payload = json.dumps(data).encode()

    signature = private_key.sign(
        payload,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    return json.dumps({
        "payload": base64.b64encode(payload).decode(),
        "signature": base64.b64encode(signature).decode()
    })


def decrypt_vote_token(token):
    private_key = load_private_key()

    encrypted = base64.b64decode(token)

    plaintext = private_key.decrypt(
        encrypted,
        padding.OAEP(
            mgf=padding.MGF1(
                algorithm=hashes.SHA256()
            ),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return json.loads(
        plaintext.decode()
    )