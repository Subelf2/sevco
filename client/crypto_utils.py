import json
import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization


def load_public_key(path="../server/server_public.pem"):
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def verify_participation_token(token: str, public_key):
    data = json.loads(token)

    payload = base64.b64decode(data["payload"])
    signature = base64.b64decode(data["signature"])

    public_key.verify(
        signature,
        payload,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    return json.loads(payload.decode())


def encrypt_vote(vote_data: dict, public_key):
    plaintext = json.dumps(vote_data).encode()

    encrypted = public_key.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return base64.b64encode(encrypted).decode()