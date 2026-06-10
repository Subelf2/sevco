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
#import json
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
                f"Votre token :\n```{token}```"
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

    votes = get_votes(session_id)

    counts = [0] * len(candidates)

    for v in votes:
        choice = v[0]
        if 0 <= choice < len(candidates):
            counts[choice] += 1

    channel = bot.get_channel(channel_id)
    if not channel:
        return

    embed = discord.Embed(
        title=f"🏁 Résultats du vote {session_id}",
        color=discord.Color.gold()
    )

    for c, n in zip(candidates, counts):
        embed.add_field(name=c, value=str(n), inline=False)

    await channel.send(embed=embed)

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

    vote_data = decrypt_vote_token(token)

    session = get_session(vote_data["session_id"])

    if not session:
        await ctx.send("Session inconnue.")
        return

    end_time = float(session[2])

    if datetime.now().timestamp() > end_time:
        await ctx.send("Vote terminé. Impossible de voter.")
        return

    register_vote(
        vote_data["participation_id"],
        vote_data["session_id"],
        vote_data["choice"]
    )

    await ctx.send("Vote enregistré.")


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
async def on_ready():
    print(
        f"Connecté comme {bot.user}"
    )

@bot.command()
async def help(ctx):
	await ctx.message.delete()
	embed = discord.Embed(title = "**Menu D'aide**", color = 0xFFD700)
	embed.add_field(name="**Liste des commandes**", value = '''
		`first` : description
		`second` : description
		''', inline = False)
	await ctx.send(embed = embed)

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