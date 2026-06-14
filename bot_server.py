import discord
from discord.ext import commands
import sqlite3
import json
import hashlib
from shared import get_db_connection, verify_client_zkp_01, verify_client_zkp_sum, verify_authority_zkp, hybrid_decrypt, SERVER_RSA_PRIV, P, G

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!server ", intents=intents)

@bot.event
async def on_ready():
    print(f"Server Bot is ready and connected as {bot.user}")

@bot.command()
async def process_vote(ctx):
    """Processes incoming RSA-encrypted votes directly from the attached file."""
    user = ctx.author

    if not ctx.message.attachments: 
        return await ctx.send("Error: Please attach your ballot.json file.")
        
    file = ctx.message.attachments[0]
    encrypted_bytes = await file.read()
    encrypted_string = encrypted_bytes.decode('utf-8')
    
    try:
        # 1. Decrypt the hybrid package using the Server's constant RSA Private Key
        decrypted_json_str = hybrid_decrypt(encrypted_string, SERVER_RSA_PRIV)
        vote_data = json.loads(decrypted_json_str)
    except Exception as e:
        return await user.send("Error: Decryption failed. The file is corrupted or not encrypted with the Server Public Key.")
    
    election_name = vote_data.get("election_name")
    pub_cred = vote_data.get("pub_cred")
    vector = vote_data.get("vector")
    zkp_sum = vote_data.get("zkp_sum")
    
    if not election_name or not pub_cred or not vector:
        return await user.send("Error: Corrupted ballot format. Missing vital election data.")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # 2. Verification of identity and double-voting prevention
    c.execute("SELECT has_voted FROM voters WHERE election_name=? AND cred_public=?", (election_name, pub_cred))
    voter = c.fetchone()
    if not voter or voter[0]:
        conn.close()
        return await user.send("Vote rejected: Invalid credential or you have already voted.")

    # 3. Fetch public key
    c.execute("SELECT pub_key FROM elections WHERE name=?", (election_name,))
    pub_key_row = c.fetchone()
    if not pub_key_row:
        conn.close()
        return await user.send("Error: Election not found on this server.")
    pub_key = pub_key_row[0]
    
    # 4. ZKP Audit 1: Disjunctive proof (each slot is 0 or 1)
    for index, slot in enumerate(vector):
        if not verify_client_zkp_01(slot["c1"], slot["c2"], pub_key, slot["zkp_01"]):
            conn.close()
            return await user.send(f"FRAUD DETECTED: Disjunctive ZKP is invalid at index {index}.")
            
    # 5. ZKP Audit 2: Sum proof (only one '1' in the vector)
    c1_sum, c2_sum = 1, 1
    for slot in vector:
        c1_sum = (c1_sum * slot["c1"]) % P
        c2_sum = (c2_sum * slot["c2"]) % P
        
    if not verify_client_zkp_sum(c1_sum, c2_sum, pub_key, zkp_sum):
        conn.close()
        return await user.send("FRAUD DETECTED: Unitary sum ZKP is invalid. Vote rejected.")

    # 6. Insert into Ballot Box
    tracking = hashlib.sha256(decrypted_json_str.encode('utf-8')).hexdigest()[:16]
    
    c.execute("INSERT INTO ballot_box (election_name, tracking_number, payload_json) VALUES (?, ?, ?)",
              (election_name, tracking, decrypted_json_str))
    c.execute("UPDATE voters SET has_voted=1 WHERE cred_public=?", (pub_cred,))
    conn.commit()
    conn.close()
    
    await user.send(f"Vote successfully audited and stored in the public ballot box.\nTracking Number: {tracking}")

# ==============================================================================
# SERVER ADMINISTRATION COMMANDS
# ==============================================================================

@bot.command()
async def init(ctx, name: str, *candidates):
    if len(candidates) < 2: return await ctx.send("Error: At least 2 candidates are required.")
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO elections (name, candidates, status) VALUES (?, ?, ?)", 
                  (name, ",".join(candidates), "WAITING"))
        conn.commit()
        await ctx.send(f"Election '{name}' created. Waiting for the authorities to join.")
    except sqlite3.IntegrityError:
        await ctx.send(f"Error: Election '{name}' already exists.")
    finally:
        conn.close()

@bot.command()
async def open(ctx, name: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT pub_key_part FROM election_authorities WHERE election_name=?", (name,))
    parts = c.fetchall()
    if len(parts) < 3: 
        conn.close()
        return await ctx.send(f"Waiting for authorities: {len(parts)}/3 are ready.")

    master_pub = 1
    for p in parts: master_pub = (master_pub * p[0]) % P

    c.execute("UPDATE elections SET pub_key=?, status='OPEN' WHERE name=?", (master_pub, name))
    conn.commit()
    conn.close()
    await ctx.send(f"Election is now OPEN. Master Public Key generated: {master_pub}")

@bot.command()
async def close(ctx, name: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT candidates FROM elections WHERE name=?", (name,))
    row = c.fetchone()
    if not row:
        conn.close()
        return await ctx.send("Error: Election not found.")
        
    nb_candidates = len(row[0].split(','))

    c.execute("SELECT payload_json FROM ballot_box WHERE election_name=?", (name,))
    ballots = [json.loads(r[0])["vector"] for r in c.fetchall()]
    
    if not ballots: 
        conn.close()
        return await ctx.send("Error: Ballot box is empty.")

    totals = [[1, 1] for _ in range(nb_candidates)]
    for vector in ballots:
        for i in range(nb_candidates):
            totals[i][0] = (totals[i][0] * vector[i]["c1"]) % P
            totals[i][1] = (totals[i][1] * vector[i]["c2"]) % P

    c.execute("UPDATE elections SET status='CLOSED', totals_json=? WHERE name=?", 
              (json.dumps(totals), name))
    conn.commit()
    conn.close()
    await ctx.send("Ballot box closed. Homomorphic totals calculated successfully.")

@bot.command()
async def tally(ctx, name: str):
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT candidates, totals_json FROM elections WHERE name=? AND status='CLOSED'", (name,))
    election_row = c.fetchone()
    if not election_row:
        conn.close()
        return await ctx.send("Error: Election not found or not closed yet.")
        
    candidates = election_row[0].split(',')
    totals = json.loads(election_row[1])

    c.execute("SELECT auth_id, pub_key_part FROM election_authorities WHERE election_name=?", (name,))
    auth_keys = {row[0]: row[1] for row in c.fetchall()}

    c.execute("SELECT auth_id, d_parts_json FROM partial_decryptions WHERE election_name=?", (name,))
    decryptions_data = c.fetchall()

    if len(decryptions_data) < 3: 
        conn.close()
        return await ctx.send(f"Waiting for decryptions: {len(decryptions_data)}/3 received.")
    conn.close()

    valid_decryptions = []
    for auth_id, d_json in decryptions_data:
        d_parts_with_zkp = json.loads(d_json)
        h_i = auth_keys[auth_id]
        
        fraud = False
        for i, data in enumerate(d_parts_with_zkp):
            if not verify_authority_zkp(totals[i][0], data["d_part"], h_i, data["zkp"]):
                await ctx.send(f"CRITICAL FRAUD: ZKP proof from Authority {auth_id} is invalid.")
                fraud = True
                break
                
        if fraud: return await ctx.send("Tally aborted due to compromised authority integrity.")
        valid_decryptions.append([data["d_part"] for data in d_parts_with_zkp])

    results = {}
    for i, candidate in enumerate(candidates):
        d_total = 1
        for d_parts_list in valid_decryptions:
            d_total = (d_total * d_parts_list[i]) % P
            
        c2_total = totals[i][1]
        d_inv = pow(d_total, P-2, P)
        g_pow_sum = (c2_total * d_inv) % P
        
        for score in range(100):
            if pow(G, score, P) == g_pow_sum:
                results[candidate] = score
                break

    embed = discord.Embed(title=f"Official Certified Results: {name}", color=0x2ecc71)
    for c, s in results.items(): 
        embed.add_field(name=c, value=f"{s} votes", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def public_urn(ctx, name: str):
    """Displays all tracking numbers for individual verifiability."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT tracking_number FROM ballot_box WHERE election_name=?", (name,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        return await ctx.send("The ballot box is currently empty.")

    hash_list = [row[0] for row in rows]
    formatted_list = "\n".join(hash_list)
    
    embed = discord.Embed(title=f"Public Urn: {name}", description="List of all encrypted ballots", color=0x3498db)
    embed.add_field(name="Tracking Numbers", value=f"```\n{formatted_list}\n```", inline=False)
    await ctx.send(embed=embed)

bot.run("")