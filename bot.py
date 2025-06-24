import os
import discord
import random
import asyncio
from discord.ext import commands
from discord import Status
from dotenv import load_dotenv

from commands.ai import AIChat
from commands.ezan import EzanNotifier
from commands.loner_bully import LonerBully
from commands.moderation import Moderation
from commands.music import Music
from commands.soundboard import setup as soundboard_setup
from commands.twitter_news import TwitterNews
from commands.utility import cycle_status, STATUSES
from commands.emsc_quake_notifier import EMSCQuakeNotifier
from commands.voice_control import VoiceControl
from commands.welcome_sound import WelcomeSound
from commands.help import Help

# Ortam değişkenlerini yükle
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("COMMAND_PREFIX", "!")

# Bot Tanımlama
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
bot.queue = []
bot.audio_lock = asyncio.Lock()
bot.music_messages = {}

async def setup(bot):
    await bot.add_cog(AIChat(bot))
    await bot.add_cog(Music(bot))
    await bot.add_cog(WelcomeSound(bot))
    await bot.add_cog(TwitterNews(bot))
    await soundboard_setup(bot)
    await bot.add_cog(LonerBully(bot))
    await bot.add_cog(EMSCQuakeNotifier(bot))
    await bot.add_cog(Help(bot))
    await bot.add_cog(VoiceControl(bot))
    await bot.add_cog(Moderation(bot))
    await bot.add_cog(EzanNotifier(bot))


@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} başarıyla giriş yaptı!")

    await bot.change_presence(
        status=Status.online,
        activity=random.choice(STATUSES)
    )

    cycle_status.start(bot)

    try:
        await bot.tree.sync()
        print(f"✅ Slash komutları Discord'a kaydedildi!")
    except Exception as e:
        print(f"❌ Slash komutları senkronize edilirken hata oluştu: {e}")

    twitter_cog = bot.get_cog("TwitterNews")
    if twitter_cog:
        await twitter_cog.start_task()

    quake_cog = bot.get_cog("EMSCQuakeNotifier")
    if quake_cog:
        await quake_cog.start_task()

@bot.event
async def on_close():
    twitter_cog = bot.get_cog("TwitterNews")
    if twitter_cog:
        twitter_cog.cog_unload()

async def main():
    try:
        await setup(bot)
        await bot.start(TOKEN)
    finally:
        twitter_cog = bot.get_cog("TwitterNews")
        if twitter_cog:
            twitter_cog.cog_unload()

import asyncio
asyncio.run(main())
