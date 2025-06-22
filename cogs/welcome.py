import random
import discord
from discord.ext import commands

from utils.tts import text_to_mp3


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot or before.channel is not None or after.channel is None:
            return
        voice_client = discord.utils.get(self.bot.voice_clients, guild=member.guild)
        if not voice_client or not voice_client.is_connected():
            return
        messages = [
            f"{member.display_name}, hoş geldin",
            f"Ooo {member.display_name}, şeref verdin",
            f"Hoş geldin {member.display_name}"
        ]
        msg = random.choice(messages)
        file_path = await text_to_mp3(msg, "welcome.mp3")
        source = discord.FFmpegPCMAudio(file_path)
        async with self.bot.get_cog("Music").audio_lock:
            voice_client.play(source)

async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
