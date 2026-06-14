import discord
import sqlite3
from discord.ext import commands
import json
from shared import get_db_connection, P, G

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!serveur ", intents=intents)

@bot.event
async def on_ready():
    print(f"🗳️ Bot Serveur prêt ({bot.user})")

@bot.command()
async def init(ctx, nom: str, *candidats):
    """Crée l'élection en BDD (Les autorités devront la rejoindre ensuite)"""
    if len(candidats) < 2: return await ctx.send("❌ Au moins 2 candidats requis.")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute("INSERT INTO elections (nom, candidats, status) VALUES (?, ?, ?)", 
                  (nom, ",".join(candidats), "WAITING"))
        conn.commit()
        await ctx.send(f"✅ Élection '{nom}' créée. En attente des 3 autorités (`!auth1 join {nom}`...)")
    except sqlite3.IntegrityError:
        # On attrape l'erreur si le nom existe déjà !
        await ctx.send(f"❌ Impossible de créer : L'élection '{nom}' existe déjà dans la base de données.")
    finally:
        conn.close()

@bot.command()
async def open(ctx, nom: str):
    """Fusionne les clés des 3 autorités et ouvre le vote"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT pub_key_part FROM election_authorities WHERE election_nom=?", (nom,))
    parts = c.fetchall()
    if len(parts) < 3: return await ctx.send(f"⏳ {len(parts)}/3 autorités prêtes.")

    master_pub = 1
    for p in parts: master_pub = (master_pub * p[0]) % P

    c.execute("UPDATE elections SET pub_key=?, status='OPEN' WHERE nom=?", (master_pub, nom))
    conn.commit()
    conn.close()
    await ctx.send(f"🟢 Élection Ouverte ! Clé Maître générée : {master_pub}")

@bot.command()
async def close(ctx, nom: str):
    """Addition homomorphe vectorielle"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT candidats FROM elections WHERE nom=?", (nom,))
    nb_candidats = len(c.fetchone()[0].split(','))

    c.execute("SELECT payload_json FROM urne WHERE election_nom=?", (nom,))
    bulletins = [json.loads(row[0]) for row in c.fetchall()]
    
    if not bulletins: return await ctx.send("❌ L'urne est vide.")

    # Initialisation des totaux à 1
    totals = [[1, 1] for _ in range(nb_candidats)]
    
    for bulletin in bulletins:
        for i in range(nb_candidats):
            totals[i][0] = (totals[i][0] * bulletin[i][0]) % P
            totals[i][1] = (totals[i][1] * bulletin[i][1]) % P

    c.execute("UPDATE elections SET status='CLOSED', totals_json=? WHERE nom=?", 
              (json.dumps(totals), nom))
    conn.commit()
    conn.close()
    await ctx.send(f"🔒 Urne fermée. Totaux homomorphes calculés. En attente des déchiffrements.")

@bot.command()
async def tally(ctx, nom: str):
    """Résolution finale des résultats"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT d_parts_json FROM partial_decryptions WHERE election_nom=?", (nom,))
    decryptions = [json.loads(row[0]) for row in c.fetchall()]
    
    if len(decryptions) < 3: return await ctx.send(f"⏳ Seulement {len(decryptions)}/3 autorités ont déchiffré.")

    c.execute("SELECT candidats, totals_json FROM elections WHERE nom=?", (nom,))
    row = c.fetchone()
    candidats = row[0].split(',')
    totals = json.loads(row[1])
    conn.close()

    resultats = {}
    for i, candidat in enumerate(candidats):
        d_total = 1
        for d in decryptions:
            d_total = (d_total * d[i]) % P
            
        c2_total = totals[i][1]
        d_inv = pow(d_total, P-2, P)
        g_pow_sum = (c2_total * d_inv) % P
        
        # Logarithme discret
        for score in range(100):
            if pow(G, score, P) == g_pow_sum:
                resultats[candidat] = score
                break

    embed = discord.Embed(title=f"🏆 Résultats Officiels : {nom}", color=0xFFD700)
    for c, s in resultats.items(): embed.add_field(name=c, value=f"{s} voix", inline=False)
    await ctx.send(embed=embed)

# ====================================================================
# COMMANDES D'ADMINISTRATION (NOUVEAU)
# ====================================================================

@bot.command()
async def list(ctx):
    """Affiche toutes les élections et leur statut"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT nom, status, candidats FROM elections")
    elections = c.fetchall()
    conn.close()

    if not elections:
        return await ctx.send("📭 Aucune élection n'existe dans la base de données.")

    embed = discord.Embed(title="📋 Liste des Élections", color=0x9b59b6)
    for nom, status, candidats in elections:
        nb_candidats = len(candidats.split(','))
        # Affichage visuel du statut
        pastille = "🟢" if status == "OPEN" else "🔒" if status == "CLOSED" else "⏳"
        embed.add_field(name=f"{pastille} {nom} [{status}]", value=f"{nb_candidats} candidats", inline=False)
        
    await ctx.send(embed=embed)

@bot.command()
async def delete(ctx, nom: str):
    """Supprime une élection spécifique et toutes ses données"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT nom FROM elections WHERE nom=?", (nom,))
    if not c.fetchone():
        conn.close()
        return await ctx.send(f"❌ L'élection '{nom}' n'existe pas.")

    # Suppression en cascade dans toutes les tables
    c.execute("DELETE FROM elections WHERE nom=?", (nom,))
    c.execute("DELETE FROM election_authorities WHERE election_nom=?", (nom,))
    c.execute("DELETE FROM partial_decryptions WHERE election_nom=?", (nom,))
    c.execute("DELETE FROM voters WHERE election_nom=?", (nom,))
    c.execute("DELETE FROM urne WHERE election_nom=?", (nom,))

    conn.commit()
    conn.close()
    await ctx.send(f"🗑️ L'élection **'{nom}'** et toutes les données associées (urne, électeurs, clés) ont été supprimées.")

@bot.command()
async def purge_all(ctx):
    """DANGER : Supprime absolument TOUTES les élections de la BDD"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM elections")
    c.execute("DELETE FROM election_authorities")
    c.execute("DELETE FROM partial_decryptions")
    c.execute("DELETE FROM voters")
    c.execute("DELETE FROM urne")
    conn.commit()
    conn.close()
    await ctx.send("☢️ **PURGE COMPLÈTE** : La base de données a été totalement réinitialisée.")

bot.run("")