import discord
from discord.ext import commands
import random
import string
import json
from shared import get_db_connection, hash_credential, hybrid_encrypt, CLIENT_RSA_PUB

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!id ", intents=intents)

@bot.event
async def on_ready():
    print(f"Credential Generator Bot is ready as {bot.user}")

@bot.command()
async def add(ctx, election_name: str, member: discord.Member):
    """Generates a secret token and sends it encrypted to the specified user."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT candidates, pub_key, status FROM elections WHERE name=?", (election_name,))
    election_data = c.fetchone()
    
    if not election_data:
        conn.close()
        return await ctx.send("Error: Election not found.")
        
    status = election_data[2]
    pub_key = election_data[1]
    
    if status != 'OPEN' or pub_key is None:
        conn.close()
        return await ctx.send("Error: The election must be OPEN before generating voter tokens.")
        
    candidates_list = election_data[0].split(',')

    priv_cred = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    pub_cred = hash_credential(priv_cred)

    c.execute("INSERT INTO voters (election_name, cred_public, has_voted) VALUES (?, ?, ?)", 
              (election_name, pub_cred, False))
    conn.commit()
    conn.close()

    token_dict = {
        "election": election_name,
        "candidates": candidates_list,
        "pub_key": pub_key,
        "priv_cred": priv_cred
    }
    
    token_json_str = json.dumps(token_dict)
    
    # Encrypt the package using the Client's constant Public RSA Key
    encrypted_token = hybrid_encrypt(token_json_str, CLIENT_RSA_PUB)

    try:
        await member.send(
            f"Here is your RSA-Encrypted Voting Token for '{election_name}'.\n"
            f"Paste this block into your local Voting App to decrypt it:\n\n"
            f"```\n{encrypted_token}\n```"
        )
        await ctx.send(f"Credential generated, RSA-encrypted, and sent to {member.mention}.")
    except discord.Forbidden:
        await ctx.send(f"Error: Cannot send Direct Messages to {member.mention}.")

bot.run("")