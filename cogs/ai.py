import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import google.generativeai as genai

from utils.tts import text_to_mp3

GEMINI_TOKEN = os.getenv("GEMINI_TOKEN")
if GEMINI_TOKEN:
    genai.configure(api_key=GEMINI_TOKEN)


class AIChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def gemini_reply(message: str) -> str:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(message)
        return response.text

    @app_commands.command(description="Yapay zeka ile sohbet")
    async def ai(self, interaction: discord.Interaction, *, mesaj: str):
        await interaction.response.defer()
        reply = self.gemini_reply(mesaj)
        await interaction.followup.send(f"🐶 **TACİ:** {reply}")

    @app_commands.command(description="Sesli yanıt")
    async def ask(self, interaction: discord.Interaction, *, mesaj: str):
        await interaction.response.defer()
        if not (interaction.user.voice and interaction.user.voice.channel):
            await interaction.followup.send("Önce bir ses kanalına gir!")
            return
        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
        reply = self.gemini_reply(mesaj)
        file_path = await text_to_mp3(reply, "ai_reply.mp3")
        source = discord.FFmpegPCMAudio(file_path)
        async with self.bot.get_cog("Music").audio_lock:
            vc.play(source)
        await interaction.followup.send("Sesli yanıt veriliyor")

async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))
