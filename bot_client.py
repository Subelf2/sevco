import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Select
import hashlib
import json
from shared import get_db_connection, encrypt_vector, hash_credential

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!client ", intents=intents)

# ====================================================================
# INTERFACE GRAPHIQUE (ÉTAPE 3 : LE MOT DE PASSE)
# ====================================================================
class VoteModal(Modal):
    def __init__(self, nom_election, candidat_choisi, candidats_liste, pub_key):
        super().__init__(title=f"Vote Secret : {nom_election}")
        self.nom = nom_election
        self.choix = candidat_choisi
        self.liste = candidats_liste
        self.pub_key = pub_key
        self.cred = TextInput(label="Votre Identifiant Secret (Credential)", style=discord.TextStyle.short)
        self.add_item(self.cred)

    async def on_submit(self, interaction: discord.Interaction):
        pub_cred = hash_credential(self.cred.value)
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("SELECT a_vote FROM voters WHERE election_nom=? AND cred_public=?", (self.nom, pub_cred))
        voter = c.fetchone()
        if not voter: 
            conn.close()
            return await interaction.response.send_message("❌ Identifiant invalide ou inconnu pour cette élection.", ephemeral=True)
        if voter[0]: 
            conn.close()
            return await interaction.response.send_message("❌ Vous avez déjà voté pour cette élection.", ephemeral=True)

        # Chiffrement Vectoriel
        bulletin_vectoriel = encrypt_vector(self.choix, self.liste, self.pub_key)
        payload_json = json.dumps(bulletin_vectoriel)
        
        tracking = hashlib.sha256(f"{payload_json}{self.cred.value}".encode()).hexdigest()[:12]
        
        c.execute("INSERT INTO urne (election_nom, tracking_number, payload_json) VALUES (?, ?, ?)",
                  (self.nom, tracking, payload_json))
        c.execute("UPDATE voters SET a_vote=1 WHERE cred_public=?", (pub_cred,))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"✅ **Vote scellé !** Votre Numéro de Suivi : `{tracking}`", ephemeral=True)

# ====================================================================
# INTERFACE GRAPHIQUE (ÉTAPE 2 : LE CHOIX DU CANDIDAT)
# ====================================================================
class CandidateSelect(Select):
    def __init__(self, nom_election, candidats, pub_key):
        self.nom = nom_election
        self.candidats = candidats
        self.pub_key = pub_key
        opts = [discord.SelectOption(label=cand) for cand in candidats]
        super().__init__(placeholder=f"Étape 2 : Choisissez un candidat...", options=opts)

    async def callback(self, inter: discord.Interaction):
        # Ouvre le pop-up du mot de passe
        await inter.response.send_modal(VoteModal(self.nom, self.values[0], self.candidats, self.pub_key))

class CandidateView(View):
    def __init__(self, nom_election, candidats, pub_key):
        super().__init__()
        self.add_item(CandidateSelect(nom_election, candidats, pub_key))

# ====================================================================
# INTERFACE GRAPHIQUE (ÉTAPE 1 : LE CHOIX DE L'ÉLECTION)
# ====================================================================
class ElectionSelect(Select):
    def __init__(self, elections_dict):
        self.elections_dict = elections_dict
        opts = [discord.SelectOption(label=nom, description=f"Voter pour l'élection {nom}") for nom in elections_dict.keys()]
        super().__init__(placeholder="Étape 1 : Choisissez l'élection...", options=opts)

    async def callback(self, inter: discord.Interaction):
        nom_choisi = self.values[0]
        candidats, pub_key = self.elections_dict[nom_choisi]
        
        # Fait disparaître le premier menu et affiche le second (Candidats) de manière invisible pour les autres (ephemeral)
        view = CandidateView(nom_choisi, candidats, pub_key)
        await inter.response.send_message(f"🏛️ **Élection sélectionnée : {nom_choisi}**\nVeuillez faire votre choix :", view=view, ephemeral=True)

class ElectionPortalView(View):
    def __init__(self, elections_dict):
        super().__init__()
        self.add_item(ElectionSelect(elections_dict))

@bot.event
async def on_ready(): print(f"💻 Bot Client prêt ({bot.user})")

# ====================================================================
# COMMANDES DU BOT CLIENT
# ====================================================================

@bot.command()
async def portail(ctx):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT nom, candidats, pub_key FROM elections WHERE status='OPEN'")
    elections_data = c.fetchall()
    conn.close()

    if not elections_data: 
        return await ctx.send("📭 Aucune élection n'est actuellement ouverte.")

    # On transforme les données en dictionnaire { "Nom": (["Alice", "Bob"], pub_key) }
    elections_dict = {}
    for row in elections_data:
        elections_dict[row[0]] = (row[1].split(','), row[2])

    embed = discord.Embed(title="🏛️ Portail de Vote Centralisé", color=0x3498db)
    embed.description = "Sélectionnez l'élection à laquelle vous souhaitez participer dans le menu déroulant ci-dessous."
    
    view = ElectionPortalView(elections_dict)
    await ctx.send(embed=embed, view=view)

bot.run("")