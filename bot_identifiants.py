import discord
from discord.ext import commands
import random
import string
from shared import get_db_connection, hash_credential

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!id ", intents=intents)

@bot.event
async def on_ready():
    print(f"🎫 Bot Générateur ID prêt ({bot.user})")

@bot.command()
async def add(ctx, nom: str, membre: discord.Member):
    priv_cred = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    pub_cred = hash_credential(priv_cred)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO voters (election_nom, cred_public, a_vote) VALUES (?, ?, ?)", 
              (nom, pub_cred, False))
    conn.commit()
    conn.close()

    try:
        await membre.send(f"🔐 Ton Identifiant pour '{nom}' : `{priv_cred}`\nVa sur le serveur et tape `!client portail` pour voter.")
        await ctx.send(f"✅ Identifiant envoyé à {membre.mention}.")
    except:
        await ctx.send(f"❌ Impossible de DM {membre.mention}.")

bot.run("")