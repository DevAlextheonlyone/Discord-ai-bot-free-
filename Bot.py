import discord
from discord.ext import commands
from discord import app_commands
import os
import threading
import time
import random
import requests
import asyncio
from flask import Flask

# ================= WEB SERVER (RENDER) =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive"

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# ================= CONFIG =================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ID = int(os.getenv("SERVER_ID"))
AI_CHANNEL_ID = int(os.getenv("AI_CHANNEL_ID"))
NUKE_ROLE_ID = int(os.getenv("NUKE_ROLE_ID"))

GUILD = discord.Object(id=SERVER_ID)

# ================= DISCORD BOT =================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ================= FALLBACK RESPONSES =================
FALLBACK_RESPONSES = [
    "Hmm, can you explain that a bit more?",
    "Interesting thought.",
    "I'm thinking about that…",
    "That’s a good question.",
    "Let’s break that down."
]

# ================= APIFREE LLM =================
def ask_apifreellm(prompt: str) -> str:
    try:
        r = requests.post(
            "https://apifreellm.com/api/chat",
            json={"message": prompt},
            timeout=25
        )

        if r.status_code != 200:
            return random.choice(FALLBACK_RESPONSES)

        data = r.json()
        return data.get("response", random.choice(FALLBACK_RESPONSES))

    except Exception:
        return random.choice(FALLBACK_RESPONSES)

# ================= NUKE STATE =================
pending_nukes = {}
NUKING = False

def has_nuke_role(member: discord.Member) -> bool:
    return any(role.id == NUKE_ROLE_ID for role in member.roles)

# ================= EVENTS =================
@bot.event
async def on_ready():
    await tree.sync(guild=GUILD)
    print(f"🤖 Logged in as {bot.user}")
    print("✅ Guild slash commands synced")

@bot.event
async def on_message(message):
    if NUKING:
        return
    if message.author.bot:
        return
    if message.channel.id != AI_CHANNEL_ID:
        return

    await message.channel.typing()

    response = await asyncio.to_thread(
        ask_apifreellm, message.content
    )

    await message.channel.send(response)

# ================= /NUKE =================
@tree.command(
    name="nuke",
    description="Prepare to delete ALL messages in the AI channel",
    guild=GUILD
)
async def nuke(interaction: discord.Interaction):

    if interaction.channel.id != AI_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ This command can only be used in the AI channel.",
            ephemeral=True
        )
        return

    if not has_nuke_role(interaction.user):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return

    pending_nukes[interaction.channel.id] = time.time()

    await interaction.response.send_message(
        "⚠️ **NUKE READY**\n"
        "Use `/nuke_confirm` within **30 seconds** to confirm.\n"
        "This will delete **ALL messages in THIS channel**.",
        ephemeral=True
    )

# ================= /NUKE_CONFIRM =================
@tree.command(
    name="nuke_confirm",
    description="CONFIRM AI channel nuke",
    guild=GUILD
)
async def nuke_confirm(interaction: discord.Interaction):

    global NUKING

    if interaction.channel.id != AI_CHANNEL_ID:
        await interaction.response.send_message(
            "❌ This command can only be used in the AI channel.",
            ephemeral=True
        )
        return

    if not has_nuke_role(interaction.user):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return

    channel_id = interaction.channel.id

    if channel_id not in pending_nukes:
        await interaction.response.send_message(
            "❌ No nuke pending.",
            ephemeral=True
        )
        return

    if time.time() - pending_nukes[channel_id] > 30:
        del pending_nukes[channel_id]
        await interaction.response.send_message(
            "❌ Nuke timed out. Run `/nuke` again.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        "💣 **NUKING CHANNEL…**",
        ephemeral=True
    )

    NUKING = True
    channel = interaction.channel

    try:
        while True:
            messages = []
            async for msg in channel.history(limit=100):
                messages.append(msg)

            if not messages:
                break

            await channel.delete_messages(messages)
            await asyncio.sleep(1)

    finally:
        NUKING = False
        del pending_nukes[channel_id]

    await channel.send("💥 **CHANNEL NUKED**")

# ================= START =================
threading.Thread(target=run_web).start()
bot.run(DISCORD_TOKEN)
