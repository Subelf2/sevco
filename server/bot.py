#=======================================================================================================================
#======================================================= Imports =======================================================
#=======================================================================================================================

import discord
from discord.ext import commands
from discord.ui import Button, View
#from PIL import Image
#from io import BytesIO

import random
import uuid
import hashlib
import asyncio

from datetime import datetime
from datetime import timedelta

from database import *
from crypto_utils import *
from config import *

#=======================================================================================================================
#===================================================== Paramètres ======================================================
#=======================================================================================================================

generate_keys()
initialize_database()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix = "$", description = "Very Secure",intents=intents)

bot.remove_command("help")

#=======================================================================================================================
#====================================================== ASCII Art ======================================================
#=======================================================================================================================

print('''
═════════════════════════════════════════════════════ BOT START ═════════════════════════════════════════════════════════
	''')

#=======================================================================================================================
#====================================================== Variables ======================================================
#=======================================================================================================================

presence_choice = [
'Very Secure',
]

active_sessions = {}

class VoteView(discord.ui.View):

    def __init__(self, session_id, candidates):
        super().__init__(timeout=None)

        self.session_id = session_id
        self.candidates = candidates

    @discord.ui.button(
        label="Participer au vote",
        style=discord.ButtonStyle.green
    )
    async def participate(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        participation_id = str(uuid.uuid4())

        token_data = {
            "session_id": self.session_id,
            "participation_id": participation_id,
            "candidates": self.candidates
        }

        token = sign_participation_token(token_data)

        try:
            await interaction.user.send(
                f"Votre token :\n```{token}```\n\nApres chiffrement via le client, envoyez le token ici avec $vote [token]"
            )

            await interaction.response.send_message(
                "Token envoyé en MP.",
                ephemeral=True
            )

        except Exception:
            await interaction.response.send_message(
                "Impossible d'envoyer un MP.",
                ephemeral=True
            )


#=======================================================================================================================
#====================================================== Fonctions ======================================================
#=======================================================================================================================

async def finalize_vote(session_id, channel_id):

    session = get_session(session_id)
    if not session:
        return

    candidates = session[1].split("|")
    votes = get_votes_with_hash(session_id)

    counts = [0] * len(candidates)
    hashes_by_candidate = [[] for _ in candidates]

    for choice, vote_hash in votes:
        if 0 <= choice < len(candidates):
            counts[choice] += 1
            hashes_by_candidate[choice].append(vote_hash)

    channel = bot.get_channel(channel_id)
    if not channel:
        return

    total = sum(counts)
    max_votes = max(counts) if total > 0 else 0
    winners = [candidates[i] for i, c in enumerate(counts) if c == max_votes]

    # ── Embed résultats ──
    embed = discord.Embed(
        title=f"🏁 Résultats du vote `{session_id}`",
        color=discord.Color.gold()
    )

    bar_width = 16
    for candidate, count in zip(candidates, counts):
        filled = round(bar_width * count / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)
        pct = round(100 * count / total) if total > 0 else 0
        embed.add_field(
            name=candidate,
            value=f"`{bar}` {count} vote(s) ({pct}%)",
            inline=False
        )

    if len(winners) == 1:
        embed.add_field(name="🥇 Vainqueur", value=winners[0], inline=False)
    else:
        embed.add_field(name="🤝 Égalité", value=" · ".join(winners), inline=False)

    embed.set_footer(text=f"{total} bulletin(s) · Contre-valeurs dans le fichier joint")

    # ── Fichier contre-valeurs ──
    import io
    col1, col2 = 22, 66
    separator = "─" * (col1 + col2 + 3)
    file_lines = [
        f"Contre-valeurs — session {session_id}",
        f"Générées le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"{'Candidat voté':<{col1}} {'Contre-valeur SHA-256':<{col2}}",
        separator,
    ]

    for choice, vote_hash in votes:
        candidate = candidates[choice] if 0 <= choice < len(candidates) else "?"
        file_lines.append(f"{candidate:<{col1}} {vote_hash}")

    file_lines += [
        separator,
        "",
        "Pour vérifier votre vote :",
        "  SHA256( <participation_id> | <numéro_du_choix> )",
        "  Votre numéro de choix : 0 = premier candidat, 1 = second, etc.",
    ]

    file_content = "\n".join(file_lines).encode("utf-8")
    file = discord.File(
        fp=io.BytesIO(file_content),
        filename=f"vote_result_{session_id}.txt"
    )

    await channel.send(embed=embed, file=file)

async def schedule_vote_end(session_id, end_time, channel_id):

    delay = end_time.timestamp() - datetime.now().timestamp()

    if delay > 0:
        await asyncio.sleep(delay)

    await finalize_vote(session_id, channel_id)

#=======================================================================================================================
#====================================================== Commandes ======================================================
#=======================================================================================================================

@bot.event
async def on_ready():
	print("Ready !!!")
	await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=random.choice(presence_choice)))

@bot.command()
async def create_vote(ctx, duration_minutes: int, *candidates):

    if len(candidates) < 2:
        await ctx.send(
            "Au moins deux candidats."
        )
        return

    session_id = str(uuid.uuid4())[:8]

    end_time = (
        datetime.now()
        + timedelta(minutes=duration_minutes)
    )

    create_session(
        session_id,
        list(candidates),
        end_time
    )

    active_sessions[session_id] = {
        "candidates": list(candidates),
        "end_time": end_time
    }

    embed = discord.Embed(
        title="Nouveau vote",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Session",
        value=session_id,
        inline=False
    )

    embed.add_field(
        name="Durée",
        value=f"{duration_minutes} minutes",
        inline=False
    )

    candidate_text = "\n".join(
        f"{i+1}. {name}"
        for i, name in enumerate(candidates)
    )

    embed.add_field(
        name="Candidats",
        value=candidate_text,
        inline=False
    )

    await ctx.send(
        embed=embed,
        view=VoteView(
            session_id,
            list(candidates)
        )
    )

    bot.loop.create_task(
    schedule_vote_end(
        session_id,
        end_time,
        ctx.channel.id
    )
)


@bot.command()
async def vote(ctx, *, token):

    try:
        vote_data = decrypt_vote_token(token)
    except Exception:
        await ctx.author.send(
            "❌ **Token de vote invalide ou corrompu.**\n"
            "Vérifiez que vous avez bien copié le token généré par le client."
        )
        return

    session = get_session(vote_data["session_id"])

    if not session:
        await ctx.author.send(
            f"❌ **Session `{vote_data['session_id']}` inconnue.**"
        )
        return

    end_time = float(session[2])

    if datetime.now().timestamp() > end_time:
        await ctx.author.send(
            "❌ **Vote terminé.** Impossible de soumettre un bulletin après la clôture."
        )
        return

    participation_id = vote_data["participation_id"]
    choice = vote_data["choice"]

    # Calcul de la contre-valeur
    raw = f"{participation_id}|{choice}".encode()
    vote_hash = hashlib.sha256(raw).hexdigest()

    register_vote(participation_id, vote_data["session_id"], choice, vote_hash)

    await ctx.author.send(
        "✅ **Vote enregistré.**\n\n"
        "Compare ta contre-valeur (affichée par le client au moment du vote) "
        "avec le tableau publié à la fin de la session pour vérifier que ton bulletin n'a pas été altéré."
    )

    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass


# @bot.command()
# async def results(ctx, session_id):

#     session = get_session(session_id)

#     if session is None:
#         await ctx.send(
#             "Session inconnue."
#         )
#         return

#     candidates = session[1].split("|")

#     counts = [0] * len(candidates)

#     votes = get_votes(session_id)

#     for vote in votes:
#         choice = vote[0]

#         if 0 <= choice < len(candidates):
#             counts[choice] += 1

#     embed = discord.Embed(
#         title=f"Résultats {session_id}",
#         color=discord.Color.gold()
#     )

#     for candidate, score in zip(
#         candidates,
#         counts
#     ):
#         embed.add_field(
#             name=candidate,
#             value=str(score)
#         )

#     await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    """Envoie l'erreur en DM à l'utilisateur."""
    msg = str(error)

    if isinstance(error, commands.MissingRequiredArgument):
        msg = f"Argument manquant : `{error.param.name}`"
    elif isinstance(error, commands.BadArgument):
        msg = f"Argument invalide : {error}"
    elif isinstance(error, commands.CommandNotFound):
        return  # on ignore silencieusement

    try:
        await ctx.author.send(
            f"❌ **Erreur sur `${ctx.command}`**\n{msg}\n\n"
            f"Utilise `$help` pour voir l'utilisation correcte."
        )
    except discord.Forbidden:
        await ctx.send(f"❌ {msg}", delete_after=10)

@bot.command()
async def help(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="📖 Aide — Vote Sécurisé",
        color=0x5b7fff
    )

    embed.add_field(
        name="`$create_vote <durée_minutes> <candidat1> <candidat2> ...`",
        value=(
            "Crée une nouvelle session de vote.\n"
            "Un bouton **Participer** est affiché dans le salon — cliquez dessus pour recevoir votre token en DM.\n"
            "**Exemple :** `$create_vote 10 Alice Bob Charlie`"
        ),
        inline=False
    )

    embed.add_field(
        name="`$vote <token>`",
        value=(
            "Soumet votre vote chiffré.\n"
            "Le token est généré par le client Python après avoir choisi votre candidat.\n"
            "**Exemple :** `$vote eyJ...`"
        ),
        inline=False
    )

    embed.add_field(
        name="🔐 Comment voter",
        value=(
            "1. Lancez `gui.py` (ou `client.py`)\n"
            "2. Collez le token reçu en DM\n"
            "3. Choisissez votre candidat\n"
            "4. Copiez le token de vote généré\n"
            "5. Envoyez-le avec `$vote <token>`"
        ),
        inline=False
    )

    embed.add_field(
        name="🧾 Contre-valeur",
        value=(
            "À la fin du vote, un tableau affiche la **contre-valeur** (hash) de chaque bulletin.\n"
            "Vous pouvez vérifier que votre vote n'a pas été altéré : "
            "votre contre-valeur = `SHA256(<participation_id>|<numéro_du_choix>)`"
        ),
        inline=False
    )

    embed.set_footer(text="Les résultats sont affichés automatiquement à la fin du vote.")
    await ctx.send(embed=embed)

@bot.command()
async def say(ctx, *text):
	await ctx.message.delete()
	await ctx.send(" ".join(text))

#=======================================================================================================================
#======================================================== Tests ========================================================
#=======================================================================================================================

@bot.command()
async def emojiotter(ctx):
	await ctx.send("<:otterbot:873289625060376686>")

@bot.command()
async def emojia(ctx):
	await ctx.send("<a:RhexeTriggered:873294395749859338>")

@bot.command()
async def button(ctx):
	button=Button(label="UwU", style=discord.ButtonStyle.green, emoji="<:otterbot:873289625060376686>")
	async def button_callback(interaction):
		await interaction.response.send_message("Button clicked")
	button.callback=button_callback
	view=View()
	view.add_item(button)
	await ctx.send("Un magnifique :sparkles: Bouton :sparkles:", view=view)

@bot.command()
async def embed(ctx):
	embed=discord.Embed(title="Un embed, rien de plus normal", description="Avec une description", color=0x1dcb1a)
	embed.set_image(url="https://i.imgflip.com/5opfk3.jpg")
	embed.set_thumbnail(url="https://is4-ssl.mzstatic.com/image/thumb/Purple111/v4/b8/ab/b5/b8abb586-12e4-c6a8-4a81-e3e0a49e06e3/mzl.dpienkcf.png/256x256bb.jpg")
	await ctx.send(embed=embed)

#======================================================== Bot Run ========================================================

bot.run(BOT_TOKEN)