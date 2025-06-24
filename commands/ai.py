import os
import discord
import random
import asyncio
import google.generativeai as genai
from discord.ext import commands
from discord import app_commands
from utils.tts import metni_sese_cevir
from dotenv import load_dotenv

load_dotenv()
GEMINI_TOKEN = os.getenv("GEMINI_TOKEN")
genai.configure(api_key=GEMINI_TOKEN)

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def gemini_cevap(mesaj: str) -> str:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(mesaj)
        return response.text

    @commands.command()
    async def ai(self, ctx, *, mesaj: str):
        await ctx.send(f"🐶 **TACİ:** {self.gemini_cevap(mesaj)}")

    @commands.command()
    async def ask(self, ctx, *, mesaj: str):
        if ctx.author.voice and ctx.author.voice.channel:
            kanal = ctx.author.voice.channel
            if not ctx.voice_client:
                await kanal.connect()

            cevap = self.gemini_cevap(mesaj)
            ses_dosyasi = await metni_sese_cevir(cevap)
            if not ses_dosyasi:
                await ctx.send("❌ Ses oluşturulamadı.")
                return

            FFMPEG_PATH = "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"
            ffmpeg_options = {'before_options': '-nostats', 'options': '-vn'}
            source = discord.FFmpegPCMAudio(ses_dosyasi, executable=FFMPEG_PATH, **ffmpeg_options)

            async with self.bot.audio_lock:
                ctx.voice_client.play(source, after=lambda e: print(f"✅ Çalındı." if not e else f"❌ Hata: {e}"))

            await ctx.send("🔊 **Sesli yanıt veriliyor...**")
        else:
            await ctx.send("Önce bir ses kanalına gir! 🎤")

    @app_commands.command(name="ai", description="Yapay zeka ile sohbet eder")
    async def slash_ai(self, interaction: discord.Interaction, mesaj: str):
        await interaction.response.defer()
        cevap = self.gemini_cevap(mesaj)
        await interaction.followup.send(f"🐶 **TACİ:** {cevap}")

    @app_commands.command(name="ask", description="Sesli kanalda yapay zeka ile konuşur")
    async def slash_ask(self, interaction: discord.Interaction, mesaj: str):
        await interaction.response.defer()

        if interaction.user.voice and interaction.user.voice.channel:
            kanal = interaction.user.voice.channel
            voice_client = interaction.guild.voice_client or await kanal.connect()

            cevap = self.gemini_cevap(mesaj)
            ses_dosyasi = await metni_sese_cevir(cevap)
            if not ses_dosyasi:
                await interaction.followup.send("❌ Ses oluşturulamadı.")
                return

            FFMPEG_PATH = "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"
            ffmpeg_options = {'before_options': '-nostats', 'options': '-vn'}
            source = discord.FFmpegPCMAudio(ses_dosyasi, executable=FFMPEG_PATH, **ffmpeg_options)

            async with self.bot.audio_lock:
                voice_client.play(source, after=lambda e: print(f"✅ Çalındı." if not e else f"❌ Hata: {e}"))

            await interaction.followup.send("🔊 **Sesli yanıt veriliyor...**")
        else:
            await interaction.followup.send("Önce bir ses kanalına gir! 🎤")
