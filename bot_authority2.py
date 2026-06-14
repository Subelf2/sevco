import discord
from discord.ext import commands
import json
from shared import init_db, generate_keys, get_db_connection, P

# --- CONFIGURATION FIXE DE L'AUTORITÉ 2 ---
AUTH_ID = "Auth2"
SECRETS_FILE = "secrets_Auth2.json"

intents = discord.Intents.default()
intents.message_content = True
# Ce bot répondra uniquement aux commandes commençant par "!auth2"
bot = commands.Bot(command_prefix="!auth2 ", intents=intents)

@bot.event
async def on_ready():
    init_db()
    print(f"🔐 Autorité {AUTH_ID} prête et connectée ({bot.user})")

@bot.command()
async def join(ctx, nom_election: str):
    priv_key, pub_key = generate_keys()
    
    try:
        with open(SECRETS_FILE, "r") as f: secrets = json.load(f)
    except FileNotFoundError:
        secrets = {}
        
    secrets[nom_election] = priv_key
    with open(SECRETS_FILE, "w") as f: json.dump(secrets, f)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO election_authorities (election_nom, auth_id, pub_key_part) VALUES (?, ?, ?)", 
              (nom_election, AUTH_ID, pub_key))
    conn.commit()
    conn.close()
    await ctx.send(f"🔑 **{AUTH_ID}** a rejoint l'élection '{nom_election}'. Clé publique partielle partagée.")

@bot.command()
async def decrypt(ctx, nom_election: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT totals_json FROM elections WHERE nom=? AND status='CLOSED'", (nom_election,))
    row = c.fetchone()
    
    if not row or not row[0]:
        conn.close()
        return await ctx.send("❌ Urne non fermée ou élection introuvable.")
        
    totals = json.loads(row[0])
    
    with open(SECRETS_FILE, "r") as f: secrets = json.load(f)
    priv_key = secrets.get(nom_election)

    d_parts = []
    for c1_total, _ in totals:
        d_parts.append(pow(c1_total, priv_key, P))

    c.execute("INSERT INTO partial_decryptions (election_nom, auth_id, d_parts_json) VALUES (?, ?, ?)", 
              (nom_election, AUTH_ID, json.dumps(d_parts)))
    conn.commit()
    conn.close()
    await ctx.send(f"🧮 **{AUTH_ID}** a soumis ses parts de déchiffrement cryptographique !")

# Remplace par le Token du 2ème bot Discord
bot.run("")