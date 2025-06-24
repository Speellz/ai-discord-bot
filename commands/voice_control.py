# commands/voice_control.py

import os
from discord.ext import commands
from discord import app_commands, FFmpegPCMAudio, Interaction
from utils.tts import metni_sese_cevir
from utils.constants import FFMPEG_PATH

class VoiceControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="join", description="Botu ses kanalına sokar")
    async def slash_join(self, interaction: Interaction):
        await interaction.response.defer()

        if interaction.user.voice:
            channel = interaction.user.voice.channel
            if not interaction.guild.voice_client:
                await channel.connect()
                await interaction.followup.send(f"🔊 **{channel.name}** kanalına bağlandım!")
            else:
                await interaction.followup.send("Zaten bir ses kanalındayım!")
        else:
            await interaction.followup.send("Önce bir ses kanalına gir! 🎤")

    @app_commands.command(name="leave", description="Botu ses kanalından çıkarır")
    async def slash_leave(self, interaction: Interaction):
        await interaction.response.defer()

        voice_client = interaction.guild.voice_client
        if voice_client:
            await voice_client.disconnect()
            await interaction.followup.send("🔇 Kanaldan ayrıldım!")
        else:
            await interaction.followup.send("Zaten bir ses kanalında değilim!")

    @app_commands.command(name="speak", description="Yazdığını sesli okur")
    async def slash_speak(self, interaction: Interaction, mesaj: str):
        await interaction.response.defer()

        if interaction.user.voice and interaction.user.voice.channel:
            kanal = interaction.user.voice.channel
            voice_client = interaction.guild.voice_client or await kanal.connect()

            ses_dosyasi = await metni_sese_cevir(mesaj)
            if not ses_dosyasi:
                await interaction.followup.send("❌ Ses oluşturulamadı.")
                return

            ffmpeg_opts = {'before_options': '-nostats', 'options': '-vn'}
            source = FFmpegPCMAudio(ses_dosyasi, executable=FFMPEG_PATH, **ffmpeg_opts)

            async with self.bot.audio_lock:
                voice_client.play(source, after=lambda e: print(f"✅ Çalındı." if not e else f"❌ Hata: {e}"))

            await interaction.followup.send("🔊 **Bot yazdığını okuyor...**")
        else:
            await interaction.followup.send("Önce bir ses kanalına gir! 🎤")
