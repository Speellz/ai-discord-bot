import os
import random
import asyncio
import discord
from discord.ext import commands, tasks
from utils.tts import text_to_mp3


class LonerBully(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_alone_since: dict[int, float] = {}
        self.messages = self.load_messages("loner_messages.txt")
        self.check_lonely_users.start()

    def load_messages(self, path: str) -> list[str]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return [m.strip() for m in f if m.strip()]
        return ["Git bi arkadaş bul."]

    @tasks.loop(seconds=30)
    async def check_lonely_users(self):
        for guild in self.bot.guilds:
            for channel in guild.voice_channels:
                members = [m for m in channel.members if not m.bot]
                if len(members) == 1:
                    user = members[0]
                    now = asyncio.get_event_loop().time()
                    if user.id not in self.user_alone_since:
                        self.user_alone_since[user.id] = now
                    elif now - self.user_alone_since[user.id] >= 60:
                        await self.bully_user(channel, user)
                        self.user_alone_since[user.id] = now + 300
                else:
                    for m in channel.members:
                        self.user_alone_since.pop(m.id, None)

    async def bully_user(self, channel: discord.VoiceChannel, user: discord.Member):
        vc = discord.utils.get(self.bot.voice_clients, guild=channel.guild)
        if not vc or not vc.is_connected():
            vc = await channel.connect()
        choice = random.choice(["sound", "speak"])
        if choice == "sound":
            sound_dir = "data/sounds"
            files = [f for f in os.listdir(sound_dir) if f.endswith(".mp3")]
            if not files:
                return
            path = os.path.join(sound_dir, random.choice(files))
            source = discord.FFmpegPCMAudio(path)
            vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(vc.disconnect(), self.bot.loop))
        else:
            msg = random.choice(self.messages)
            file_path = await text_to_mp3(msg, "loner.mp3")
            source = discord.FFmpegPCMAudio(file_path)
            vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(vc.disconnect(), self.bot.loop))

    @check_lonely_users.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(LonerBully(bot))
