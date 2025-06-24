import discord
import random
from discord.ext import commands
from utils.welcome_messages import WELCOME_MESSAGES
from utils.tts import metni_sese_cevir

class WelcomeSound(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        if before.channel is None and after.channel is not None:
            kanal = after.channel
            voice_client = discord.utils.get(self.bot.voice_clients, guild=member.guild)

            if voice_client and voice_client.is_connected():
                mesaj = random.choice(WELCOME_MESSAGES).format(name=member.display_name)
                ses_dosyasi = await metni_sese_cevir(mesaj, dosya_adi="hosgeldin.mp3")

                ffmpeg_path = "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"
                ffmpeg_options = {
                    'before_options': '-nostats',
                    'options': '-vn'
                }

                source = discord.FFmpegPCMAudio(ses_dosyasi, executable=ffmpeg_path, **ffmpeg_options)

                async with self.bot.audio_lock:
                    voice_client.play(source, after=lambda e: print(
                        f"✅ Ses başarıyla çalındı." if not e else f"❌ Hata: {e}"))
