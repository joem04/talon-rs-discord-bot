# External imports
import discord 
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

TOKEN = os.getenv('TOKEN')

# Check if token exists, if not exit - will update with better error handling
if TOKEN is None:
    exit(1)

# Init bot
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Load cogs only once during startup
async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')  # Await here
                print(f"[✓] Loaded {filename}")
            except Exception as e:
                print(f"[!] Failed to load {filename}: {e}")


# Sync / commands on bot startup and load cogs
@bot.event
async def on_ready():
    try:
        synced_commands = await bot.tree.sync()
        print(f"[✓] Synced {len(synced_commands)} Commands.")
    except Exception as e:
        print("[!] Error syncing commands: {e}")


# Start the bot and load cogs
async def main():
    await load_cogs()  # Load cogs before running the bot
    await bot.start(TOKEN)


# To run the bot
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except discord.LoginFailure as e:
        print('Login failed: please check discord token.')
    except Exception as e:
        print(f'An unexpected error has occurred: {e}')

    
