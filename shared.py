import sqlite3
import random
import hashlib
import json

# --- PARAMÈTRES CRYPTO JOUETS ---
P = 107
G = 2

def generate_keys():
    priv = random.randint(1, P-2)
    pub = pow(G, priv, P)
    return priv, pub

def encrypt_vector(choix_candidat, liste_candidats, pub_key):
    """Chiffre 1 pour le candidat choisi, 0 pour les autres"""
    bulletin = []
    for candidat in liste_candidats:
        vote_val = 1 if candidat == choix_candidat else 0
        r = random.randint(1, P-2)
        c1 = pow(G, r, P)
        c2 = (pow(pub_key, r, P) * pow(G, vote_val, P)) % P
        bulletin.append((c1, c2))
    return bulletin

def hash_credential(priv_cred):
    return hashlib.sha256(priv_cred.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect('belenios.db')
    c = conn.cursor()
    # L'élection stocke le JSON des totaux chiffrés
    c.execute('''CREATE TABLE IF NOT EXISTS elections
                 (nom TEXT PRIMARY KEY, candidats TEXT, pub_key INTEGER, totals_json TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS election_authorities
                 (election_nom TEXT, auth_id TEXT, pub_key_part INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS partial_decryptions
                 (election_nom TEXT, auth_id TEXT, d_parts_json TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS voters
                 (election_nom TEXT, cred_public TEXT, a_vote BOOLEAN)''')
    # L'urne stocke le JSON du bulletin vectoriel (et on retire le nom en clair pour un secret total !)
    c.execute('''CREATE TABLE IF NOT EXISTS urne
                 (election_nom TEXT, tracking_number TEXT, payload_json TEXT)''')
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect('belenios.db')