import discord
from discord.ext import commands, tasks
import asyncio
import random
import os
from pydub import AudioSegment
import edge_tts

FFMPEG_PATH = "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"

class LonerBully(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_alone_since = {}
        self.messages = self.load_messages("loner_messages.txt")
        self.check_lonely_users.start()

    def load_messages(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
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
                        print(f"👀 {user.display_name} 1 dakikadır yalnız, operasyon başlatılıyor...")
                        await self.bully_user(channel, user)
                        self.user_alone_since[user.id] = now + 300
                else:
                    for m in channel.members:
                        self.user_alone_since.pop(m.id, None)

    async def bully_user(self, channel, user):
        voice_client = discord.utils.get(self.bot.voice_clients, guild=channel.guild)
        if not voice_client or not voice_client.is_connected():
            voice_client = await channel.connect()

        choice = random.choice(["soundfile", "speak"])

        async def disconnect_after_playing(error=None):
            if error:
                print(f"❌ Ses çalma hatası: {error}")
            try:
                await voice_client.disconnect()
            except Exception as e:
                print(f"❌ Bağlantı kesme hatası: {e}")

        if choice == "soundfile":
            sound_dir = "data/sounds"
            sound_files = [f for f in os.listdir(sound_dir) if f.endswith(".mp3")]
            if not sound_files:
                print("❌ Ses dosyası bulunamadı.")
                await disconnect_after_playing()
                return

            selected_sound = random.choice(sound_files)
            file_path = os.path.join(sound_dir, selected_sound)

            print(f"📢 {user.display_name} için çalınacak dosya: {selected_sound}")
            source = discord.FFmpegPCMAudio(file_path, executable=FFMPEG_PATH)
            voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(disconnect_after_playing(e),
                                                                                       self.bot.loop))

        else:
            mesaj = random.choice(self.messages)
            dosya_adi = "data/sounds/yalniz.mp3"

            tts = edge_tts.Communicate(mesaj, voice="tr-TR-AhmetNeural")
            await tts.save(dosya_adi)

            audio = AudioSegment.from_mp3(dosya_adi)
            audio = audio.set_frame_rate(44100).set_channels(2)
            audio.export(dosya_adi, format="mp3", bitrate="192k")

            print(f"📢 {user.display_name} için konuşma: {mesaj}")
            source = discord.FFmpegPCMAudio(dosya_adi, executable=FFMPEG_PATH)
            voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(disconnect_after_playing(e),
                                                                                       self.bot.loop))

    @check_lonely_users.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()