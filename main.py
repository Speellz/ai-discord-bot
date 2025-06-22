import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("COMMAND_PREFIX", "!")

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=PREFIX, intents=intents)


async def load_cogs():
    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    twitter = bot.get_cog("TwitterNews")
    if twitter:
        await twitter.check_tweets.start()
    await bot.change_presence(status=discord.Status.online)
    try:
        await bot.tree.sync()
        print("Slash commands synced")
    except Exception as e:
        print(f"Sync error: {e}")


async def main():
    await load_cogs()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
