import os
import discord
from discord.ext import commands
import aiohttp
import asyncio
from aiohttp import web

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def fetch_openrouter(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as resp:
            if resp.status == 200:
                js = await resp.json()
                return js["choices"][0]["message"]["content"]
            else:
                return f"❌ API Error: {resp.status}"

async def get_ai_response(content: str) -> str:
    """Get AI response for any message content"""
    try:
        response = await fetch_openrouter(content)
        # Discord has a 2000 character limit
        if len(response) > 2000:
            response = response[:1997] + "..."
        return response
    except Exception as e:
        return f"❌ Error: {str(e)}"

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.command(name='ping')
async def ping_command(ctx):
    """Simple ping command to test if bot is working"""
    if ctx.channel.id == ALLOWED_CHANNEL_ID:
        await ctx.send("🏓 Pong! Bot is working!")

@bot.tree.command(name="chat", description="Chat with the AI assistant")
async def chat_command(interaction: discord.Interaction, message: str):
    """Slash command for chatting with AI"""
    if interaction.channel.id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message("❌ This command can only be used in the allowed channel.", ephemeral=True)
        return
    
    await interaction.response.defer()
    response = await get_ai_response(message)
    await interaction.followup.send(response)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != ALLOWED_CHANNEL_ID:
        return
    
    # Process prefix commands first
    await bot.process_commands(message)
    
    # If it's a prefix command, don't respond with AI
    if message.content.startswith('!'):
        return
    
    # Respond to regular messages with AI
    async with message.channel.typing():
        response = await get_ai_response(message.content)
        await message.reply(response)

async def create_web_server():

bot.run(DISCORD_TOKEN)