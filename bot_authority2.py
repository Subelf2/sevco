import discord
from discord.ext import commands
import json
from shared import init_db, generate_keys, get_db_connection, generate_authority_zkp, P, G

# --- CONFIGURATION ---
AUTH_ID = "Auth2"
SECRETS_FILE = f"secrets_{AUTH_ID}.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=f"!{AUTH_ID.lower()} ", intents=intents)

@bot.event
async def on_ready():
    init_db()
    print(f"Authority {AUTH_ID} connected as {bot.user}")

@bot.command()
async def join(ctx, election_name: str):
    """Generates key part and joins the election securely."""
    priv_key, pub_key = generate_keys()
    
    try:
        with open(SECRETS_FILE, "r") as f: secrets = json.load(f)
    except FileNotFoundError:
        secrets = {}
        
    secrets[election_name] = priv_key
    with open(SECRETS_FILE, "w") as f: json.dump(secrets, f)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM election_authorities WHERE election_name=? AND auth_id=?", (election_name, AUTH_ID))
    c.execute("INSERT INTO election_authorities (election_name, auth_id, pub_key_part) VALUES (?, ?, ?)", 
              (election_name, AUTH_ID, pub_key))
    conn.commit()
    conn.close()
    await ctx.send(f"Authority {AUTH_ID} has successfully joined election '{election_name}'.")

@bot.command()
async def decrypt(ctx, election_name: str):
    """Submits partial decryptions with ZKPs for tallying."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT totals_json FROM elections WHERE name=? AND status='CLOSED'", (election_name,))
    row = c.fetchone()
    
    if not row or not row[0]:
        conn.close()
        return await ctx.send("Error: Ballot box not closed or election not found.")
        
    totals = json.loads(row[0])
    
    with open(SECRETS_FILE, "r") as f: secrets = json.load(f)
    priv_key = secrets.get(election_name)

    c.execute("SELECT pub_key_part FROM election_authorities WHERE election_name=? AND auth_id=?", (election_name, AUTH_ID))
    h_i = c.fetchone()[0]

    d_parts_with_zkp = []
    for c1_total, c2_total in totals:
        d_part = pow(c1_total, priv_key, P)
        zkp = generate_authority_zkp(c1_total, d_part, priv_key, h_i)
        d_parts_with_zkp.append({"d_part": d_part, "zkp": zkp})

    c.execute("DELETE FROM partial_decryptions WHERE election_name=? AND auth_id=?", (election_name, AUTH_ID))
    c.execute("INSERT INTO partial_decryptions (election_name, auth_id, d_parts_json) VALUES (?, ?, ?)", 
              (election_name, AUTH_ID, json.dumps(d_parts_with_zkp)))
    conn.commit()
    conn.close()
    await ctx.send(f"Authority {AUTH_ID} has submitted partial decryptions certified by ZKP.")

bot.run("")