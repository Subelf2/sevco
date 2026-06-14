import sqlite3
import random
import hashlib
import json
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet

import sqlite3
import random
import hashlib
import json
import base64
import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet

# ==============================================================================
# CONSTANT RSA KEYS (Shared via local files)
# ==============================================================================

def _load_or_generate_rsa(filename):
    """Charge une clé RSA depuis un fichier, ou la crée si elle n'existe pas."""
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            pem_data = f.read()
        return serialization.load_pem_private_key(pem_data, password=None)
    else:
        priv_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem_data = priv_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(filename, "wb") as f:
            f.write(pem_data)
        return priv_key

# Ces clés seront désormais physiquement identiques pour tous les programmes
_server_private_key = _load_or_generate_rsa("server_rsa.pem")
_client_private_key = _load_or_generate_rsa("client_rsa.pem")

SERVER_RSA_PUB = _server_private_key.public_key()
SERVER_RSA_PRIV = _server_private_key
CLIENT_RSA_PUB = _client_private_key.public_key()
CLIENT_RSA_PRIV = _client_private_key

# ==============================================================================
# HYBRID ENCRYPTION (RSA + AES) FOR LARGE PAYLOADS
# ==============================================================================

def hybrid_encrypt(payload_string, recipient_pub_key):
    """Encrypts a large payload using an ephemeral AES key, then encrypts the AES key with RSA."""
    aes_key = Fernet.generate_key()
    cipher_aes = Fernet(aes_key)
    
    encrypted_payload = cipher_aes.encrypt(payload_string.encode('utf-8'))
    
    encrypted_aes_key = recipient_pub_key.encrypt(
        aes_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )
    
    combined = base64.b64encode(encrypted_aes_key).decode('utf-8') + "|||" + base64.b64encode(encrypted_payload).decode('utf-8')
    return combined

def hybrid_decrypt(combined_payload, recipient_priv_key):
    """Decrypts the AES key using RSA, then decrypts the payload using AES."""
    parts = combined_payload.split("|||")
    if len(parts) != 2:
        raise ValueError("Invalid encrypted package format.")
        
    encrypted_aes_key = base64.b64decode(parts[0])
    encrypted_payload = base64.b64decode(parts[1])
    
    aes_key = recipient_priv_key.decrypt(
        encrypted_aes_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )
    
    cipher_aes = Fernet(aes_key)
    decrypted_payload = cipher_aes.decrypt(encrypted_payload).decode('utf-8')
    return decrypted_payload

# ==============================================================================
# ELGAMAL CRYPTOGRAPHIC PARAMETERS
# ==============================================================================
P = 107
G = 2

def generate_keys():
    priv = random.randint(1, P-2)
    pub = pow(G, priv, P)
    return priv, pub

def hash_credential(priv_cred):
    return hashlib.sha256(priv_cred.encode()).hexdigest()

# ==============================================================================
# ZERO-KNOWLEDGE PROOFS (ZKP)
# ==============================================================================

def generate_authority_zkp(C1, D, x, h):
    w = random.randint(1, P-2)
    a = pow(G, w, P)
    b = pow(C1, w, P)
    hash_in = f"{G},{h},{C1},{D},{a},{b}".encode()
    c = int(hashlib.sha256(hash_in).hexdigest(), 16) % (P-1)
    s = (w + c * x) % (P-1)
    return {"a": a, "b": b, "c": c, "s": s}

def verify_authority_zkp(C1, D, h, proof):
    a, b, c, s = proof["a"], proof["b"], proof["c"], proof["s"]
    hash_in = f"{G},{h},{C1},{D},{a},{b}".encode()
    expected_c = int(hashlib.sha256(hash_in).hexdigest(), 16) % (P-1)
    if expected_c != c: return False
    if pow(G, s, P) != (a * pow(h, c, P)) % P: return False
    if pow(C1, s, P) != (b * pow(D, c, P)) % P: return False
    return True

def generate_client_zkp_01(C1, C2, r, v, pub_key):
    if v == 1:
        c0 = random.randint(1, P-2)
        s0 = random.randint(1, P-2)
        a0 = (pow(G, s0, P) * pow(C1, P-1-c0, P)) % P
        b0 = (pow(pub_key, s0, P) * pow(C2, P-1-c0, P)) % P
        w1 = random.randint(1, P-2)
        a1 = pow(G, w1, P)
        b1 = pow(pub_key, w1, P)
        challenge = int(hashlib.sha256(f"{C1},{C2},{a0},{b0},{a1},{b1}".encode()).hexdigest(), 16) % (P-1)
        c1 = (challenge - c0) % (P-1)
        s1 = (w1 + c1 * r) % (P-1)
    else:
        c1 = random.randint(1, P-2)
        s1 = random.randint(1, P-2)
        a1 = (pow(G, s1, P) * pow(C1, P-1-c1, P)) % P
        C2_over_g = (C2 * pow(G, P-2, P)) % P
        b1 = (pow(pub_key, s1, P) * pow(C2_over_g, P-1-c1, P)) % P
        w0 = random.randint(1, P-2)
        a0 = pow(G, w0, P)
        b0 = pow(pub_key, w0, P)
        challenge = int(hashlib.sha256(f"{C1},{C2},{a0},{b0},{a1},{b1}".encode()).hexdigest(), 16) % (P-1)
        c0 = (challenge - c1) % (P-1)
        s0 = (w0 + c0 * r) % (P-1)
    return {"a0": a0, "b0": b0, "a1": a1, "b1": b1, "c0": c0, "c1": c1, "s0": s0, "s1": s1}

def verify_client_zkp_01(C1, C2, pub_key, proof):
    a0, b0, a1, b1 = proof["a0"], proof["b0"], proof["a1"], proof["b1"]
    c0, c1, s0, s1 = proof["c0"], proof["c1"], proof["s0"], proof["s1"]
    challenge = int(hashlib.sha256(f"{C1},{C2},{a0},{b0},{a1},{b1}".encode()).hexdigest(), 16) % (P-1)
    
    if (c0 + c1) % (P-1) != challenge: return False
    if pow(G, s0, P) != (a0 * pow(C1, c0, P)) % P: return False
    if pow(pub_key, s0, P) != (b0 * pow(C2, c0, P)) % P: return False
    
    C2_over_g = (C2 * pow(G, P-2, P)) % P
    if pow(G, s1, P) != (a1 * pow(C1, c1, P)) % P: return False
    if pow(pub_key, s1, P) != (b1 * pow(C2_over_g, c1, P)) % P: return False
    return True

def generate_client_zkp_sum(C1_sum, C2_sum, R_sum, pub_key):
    w = random.randint(1, P-2)
    a = pow(G, w, P)
    b = pow(pub_key, w, P)
    hash_in = f"{G},{pub_key},{C1_sum},{C2_sum},{a},{b}".encode()
    c = int(hashlib.sha256(hash_in).hexdigest(), 16) % (P-1)
    s = (w + c * R_sum) % (P-1)
    return {"a": a, "b": b, "c": c, "s": s}

def verify_client_zkp_sum(C1_sum, C2_sum, pub_key, proof):
    a, b, c, s = proof["a"], proof["b"], proof["c"], proof["s"]
    hash_in = f"{G},{pub_key},{C1_sum},{C2_sum},{a},{b}".encode()
    expected_c = int(hashlib.sha256(hash_in).hexdigest(), 16) % (P-1)
    
    if expected_c != c: return False
    C2_over_g = (C2_sum * pow(G, P-2, P)) % P
    if pow(G, s, P) != (a * pow(C1_sum, c, P)) % P: return False
    if pow(pub_key, s, P) != (b * pow(C2_over_g, c, P)) % P: return False
    return True

# ==============================================================================
# VOTE ENCRYPTION
# ==============================================================================

def encrypt_vector(chosen_candidate, candidate_list, pub_key):
    ballot = []
    C1_sum, C2_sum, R_sum = 1, 1, 0
    
    for candidate in candidate_list:
        v = 1 if candidate == chosen_candidate else 0
        r = random.randint(1, P-2)
        c1 = pow(G, r, P)
        c2 = (pow(pub_key, r, P) * pow(G, v, P)) % P
        
        zkp_01 = generate_client_zkp_01(c1, c2, r, v, pub_key)
        ballot.append({"c1": c1, "c2": c2, "zkp_01": zkp_01})
        
        C1_sum = (C1_sum * c1) % P
        C2_sum = (C2_sum * c2) % P
        R_sum = (R_sum + r) % (P-1)
        
    zkp_sum = generate_client_zkp_sum(C1_sum, C2_sum, R_sum, pub_key)
    return {"vector": ballot, "zkp_sum": zkp_sum}

# ==============================================================================
# DATABASE INITIALIZATION
# ==============================================================================

def init_db():
    conn = sqlite3.connect('belenios.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS elections
                 (name TEXT PRIMARY KEY, candidates TEXT, pub_key INTEGER, totals_json TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS election_authorities
                 (election_name TEXT, auth_id TEXT, pub_key_part INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS partial_decryptions
                 (election_name TEXT, auth_id TEXT, d_parts_json TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS voters
                 (election_name TEXT, cred_public TEXT, has_voted BOOLEAN)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ballot_box
                 (election_name TEXT, tracking_number TEXT, payload_json TEXT)''')
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect('belenios.db')