import discord
from discord.ext import commands
import os
import time
import random
import requests

# ================= CONFIG =================
AI_CHANNEL_ID = int(os.getenv("AI_CHANNEL_ID"))  # kanal-ID
AI_URL = "https://apifreellm.com/api/chat"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= AI CALL =================
def ask_ai(prompt: str) -> str:
    try:
        r = requests.post(
            AI_URL,
            headers={"Content-Type": "application/json"},
            json={"message": prompt},
            timeout=30
        )
        data = r.json()
        return data.get("response", "I could not generate a response.")
    except Exception:
        return "The AI is currently unavailable."

# ================= EVENTS =================
@bot.event
async def on_ready():
    print(f"🤖 Free AI bot running as {bot.user}")
    print(f"📢 Listening only in channel ID: {AI_CHANNEL_ID}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # endast rätt kanal
    if message.channel.id != AI_CHANNEL_ID:
        return

    # ignorera kommandon (om du vill lägga till senare)
    if message.content.startswith("!"):
        return

    await message.channel.typing()
    time.sleep(random.randint(2, 4))

    reply = ask_ai(message.content)
    await message.channel.send(reply[:2000])

# ================= START =================
bot.run(os.getenv("DISCORD_TOKEN"))
