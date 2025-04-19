import os
import discord
import edge_tts
import asyncio
from discord.ext import commands
import yt_dlp
from discord import app_commands
from discord import Status, Activity, ActivityType
from dotenv import load_dotenv
from pydub import AudioSegment
from commands.loner_bully import LonerBully
from commands.soundboard import setup as soundboard_setup
from commands.twitter_news import TwitterNews
from commands.utility import cycle_status, STATUSES
import google.generativeai as genai
import random

# Ortam değişkenlerini yükle
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("COMMAND_PREFIX", "!")
GEMINI_TOKEN = os.getenv("GEMINI_TOKEN")

# API'yi yapılandır
genai.configure(api_key=GEMINI_TOKEN)

# Bot Tanımlama
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
bot.queue = []
bot.audio_lock = asyncio.Lock()
bot.music_messages = {}


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.currently_playing = None

    @commands.command()
    async def join(self, ctx):
        """Botu ses kanalına sokar"""
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if ctx.voice_client is None:
                await channel.connect()
                await ctx.send(f"🔊 **{channel.name}** kanalına bağlandım!")
            else:
                await ctx.send("Ben zaten bir ses kanalındayım!")
        else:
            await ctx.send("Önce bir ses kanalına gir!")

    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            self.queue.clear()
            await ctx.send("🔇 Kanaldan ayrıldım ve kuyruğu temizledim!")
        else:
            await ctx.send("Ben zaten bir ses kanalında değilim!")

    async def start_playing(self, ctx, url):
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            title = info['title']

        if ctx.voice_client.is_playing():
            self.queue.append((url2, title))
            await ctx.send(f"📥 **Sıraya eklendi:** {title}")
        else:
            self.currently_playing = title
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn -bufsize 64k'
            }
            source = discord.FFmpegPCMAudio(url2, **ffmpeg_options)

            def after_playing(error):
                if error:
                    print(f"Şarkı oynatılırken hata oluştu: {error}")
                asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

            async with self.bot.audio_lock:
                ctx.voice_client.play(source, after=after_playing)

            await ctx.send(f"🎶 **Şimdi Çalıyor:** {title}")

    async def play_next(ctx):
        voice_client = ctx.guild.voice_client

        if bot.queue:
            next_url, next_title = bot.queue.pop(0)

            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -timeout 3000000',
                'options': '-vn'
            }
            source = discord.FFmpegPCMAudio(next_url, **ffmpeg_options)

            def after_playing(error):
                if error:
                    print(f"Hata oluştu: {error}")
                asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

            async with bot.audio_lock:
                voice_client.play(source, after=after_playing)

            await ctx.send(f"🎶 **Şimdi Çalıyor:** {next_title}")
        else:
            await ctx.send("🎵 **Kuyruktaki tüm şarkılar çalındı!**")

    @commands.command()
    async def play(self, ctx, *, url_or_search):
        """Müzik çalar"""
        if not ctx.voice_client:
            await ctx.invoke(self.join)

        if url_or_search.startswith("http"):
            url = url_or_search
        else:
            search_url = f"ytsearch:{url_or_search}"
            ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'noplaylist': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                url = info['entries'][0]['url']
                await ctx.send(f"🎶 **Şarkı Bulundu:** {info['entries'][0]['title']}")

        await self.start_playing(ctx, url)

    @commands.command()
    async def skip(self, ctx):
        """Şarkıyı atlar"""
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏭ **Şarkı geçildi!**")
        else:
            await ctx.send("Şu anda çalan bir şarkı yok!")

    @commands.command()
    async def pause(self, ctx):
        """Şarkıyı duraklatır"""
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸ **Şarkı duraklatıldı!**")
        else:
            await ctx.send("Şu anda çalan bir şarkı yok!")

    @commands.command()
    async def resume(self, ctx):
        """Duraklatılmış şarkıyı devam ettirir"""
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶ **Şarkı devam ediyor!**")
        else:
            await ctx.send("Duraklatılmış bir şarkı yok!")

    @commands.command()
    async def nowplaying(self, ctx):
        """Şu an çalan şarkıyı gösterir"""
        if self.currently_playing:
            await ctx.send(f"🎶 **Şu anda çalan şarkı:** {self.currently_playing}")
        else:
            await ctx.send("Şu anda çalan bir şarkı yok!")

class WelcomeSound(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def metni_sese_cevir(self, metin: str, dosya_adi="hosgeldin.mp3"):
        print(f"🎙 '{metin}' mesajı sese çevriliyor...")

        tts = edge_tts.Communicate(metin, voice="tr-TR-AhmetNeural")
        await tts.save(dosya_adi)

        audio = AudioSegment.from_mp3(dosya_adi)
        audio = audio.set_frame_rate(44100).set_channels(2)
        audio.export(dosya_adi, format="mp3", bitrate="192k")

        return dosya_adi

@commands.Cog.listener()
async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        if before.channel is None and after.channel is not None:
            kanal = after.channel
            print(f"👤 {member.display_name} ses kanalına katıldı: {kanal.name}")

            voice_client = discord.utils.get(self.bot.voice_clients, guild=member.guild)

            if voice_client and voice_client.is_connected():
                print("✅ Bot zaten bir ses kanalında. Hoş geldin mesajı oynatılıyor...")

                mesajlar = [
                    f"{member.display_name}, hoş geldin",
                    f"Ooo {member.display_name}, şeref verdin amına koyduğum",
                    f"{member.display_name}, yine mi sen geldin amına koyim ya",
                    f"Hoş geldin {member.display_name}, ortam şenlendi aç götünü",
                    f"Kral geldi, {member.display_name} burada!",
                    f"{member.display_name}, geri git gelme",
                    f"{member.display_name}, geldi yine tipini siktiğim",
                    f"Geldin de ne oldu {member.display_name}?",
                    f"Hey {member.display_name}, amına koyim",
                    f"{member.display_name}, geldi ben çıkıyorum beyler "
                ]
                mesaj = random.choice(mesajlar)
                print(f"📢 Seçilen mesaj: {mesaj}")

                ses_dosyasi = await self.metni_sese_cevir(mesaj)

                FFMPEG_PATH = "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"
                ffmpeg_options = {
                    'before_options': '-nostats',
                    'options': '-vn'
                }

                if voice_client and voice_client.is_connected():
                    source = discord.FFmpegPCMAudio(ses_dosyasi, executable=FFMPEG_PATH, **ffmpeg_options)

                    async with self.bot.audio_lock:
                        voice_client.play(source, after=lambda e: print(
                            f"✅ Ses başarıyla çalındı." if not e else f"❌ Hata: {e}"))

async def metni_sese_cevir(metin: str, dosya_adi="cevap.mp3"):
    print("🔄 Edge TTS ile ses dönüştürülüyor...")
    tts = edge_tts.Communicate(metin, voice="tr-TR-AhmetNeural")
    await tts.save(dosya_adi)

    print("🎙 Ses dosyası optimize ediliyor...")
    audio = AudioSegment.from_mp3(dosya_adi)
    audio = audio.set_frame_rate(44100).set_channels(2)
    audio.export(dosya_adi, format="mp3", bitrate="192k")

    print(f"✅ Ses dosyası başarıyla oluşturuldu: {os.path.abspath(dosya_adi)}")
    return dosya_adi

@bot.tree.command(name="join", description="Botu ses kanalına sokar")
async def slash_join(interaction: discord.Interaction):
    await interaction.response.defer()
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        if not interaction.guild.voice_client:
            await channel.connect()
            await interaction.followup.send(f"🔊 **{channel.name}** kanalına bağlandım!")
        else:
            await interaction.followup.send("Ben zaten bir ses kanalındayım!")
    else:
        await interaction.followup.send("Önce bir ses kanalına gir!")

@bot.tree.command(name="leave", description="Botu ses kanalından çıkarır")
async def slash_leave(interaction: discord.Interaction):
    await interaction.response.defer()
    voice_client = interaction.guild.voice_client

    if voice_client:
        await voice_client.disconnect()
        await interaction.followup.send("🔇 Kanaldan ayrıldım ve kuyruğu temizledim!")
    else:
        await interaction.followup.send("Ben zaten bir ses kanalında değilim!")

@bot.tree.command(name="play", description="Şarkı çalar")
async def slash_play(interaction: discord.Interaction, song: str):
    await interaction.response.defer()
    voice_client = interaction.guild.voice_client

    if not voice_client:
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            voice_client = await channel.connect()
        else:
            await interaction.followup.send("Önce bir ses kanalına gir!")
            return

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{song}" if not song.startswith("http") else song, download=False)
        url = info['entries'][0]['url'] if 'entries' in info else info['url']
        title = info['entries'][0]['title'] if 'entries' in info else info['title']

    if voice_client.is_playing():
        bot.queue.append((url, title))
        await interaction.followup.send(f"📥 **Sıraya eklendi:** {title}")
    else:
        source = discord.FFmpegPCMAudio(url)

        async with bot.audio_lock:
            voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(interaction), bot.loop))

        embed = discord.Embed(title="🎶 Şimdi Çalıyor:", description=f"**{title}**", color=discord.Color.blue())
        message = await interaction.followup.send(embed=embed)

        controls = ["⏪", "⏸", "▶", "⏩", "⏹"]
        for emoji in controls:
            await message.add_reaction(emoji)

        bot.music_messages[message.id] = interaction.channel.id

async def play_next(ctx):
    voice_client = ctx.guild.voice_client

    if bot.queue:
        next_url, next_title = bot.queue.pop(0)

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -timeout 3000000',
            'options': '-vn'
        }
        source = discord.FFmpegPCMAudio(next_url, **ffmpeg_options)

        def after_playing(error):
            if error:
                print(f"Hata oluştu: {error}")
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        voice_client.play(source, after=after_playing)
        await ctx.send(f"🎶 **Şimdi Çalıyor:** {next_title}")
    else:
        await ctx.send("🎵 **Kuyruktaki tüm şarkılar çalındı!**")

@bot.tree.command(name="skip", description="Şarkıyı atlar")
async def slash_skip(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    await ctx.invoke(bot.get_command("skip"))


@bot.tree.command(name="pause", description="Şarkıyı duraklatır")
async def slash_pause(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    await ctx.invoke(bot.get_command("pause"))


@bot.tree.command(name="resume", description="Duraklatılmış şarkıyı devam ettirir")
async def slash_resume(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    await ctx.invoke(bot.get_command("resume"))


@bot.tree.command(name="clear", description="Müzik kuyruğunu temizler")
async def slash_clear(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    await ctx.invoke(bot.get_command("clear"))


@bot.tree.command(name="nowplaying", description="Şu anda çalan şarkıyı gösterir")
async def slash_nowplaying(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    await ctx.invoke(bot.get_command("nowplaying"))


@bot.tree.command(name="volume", description="Botun ses seviyesini ayarlar (0-100)")
async def slash_volume(interaction: discord.Interaction, volume: int):
    ctx = await bot.get_context(interaction)
    await ctx.invoke(bot.get_command("volume"), volume=volume)


@bot.tree.command(name="queue", description="Müzik kuyruğunu gösterir")
async def slash_queue(interaction: discord.Interaction):
    ctx = await bot.get_context(interaction)
    await ctx.invoke(bot.get_command("queue"))


@bot.tree.command(name="remove", description="Kuyruktan belirtilen şarkıyı kaldırır")
async def slash_remove(interaction: discord.Interaction, index: int):
    ctx = await bot.get_context(interaction)
    await ctx.invoke(bot.get_command("remove"), index=index)

@bot.tree.command(name="play_sound", description="Soundboard'dan belirlenen sesi çalar")
async def slash_play_sound(interaction: discord.Interaction, sound_name: str):
    await interaction.response.defer()

    soundboard_cog = bot.get_cog("Soundboard")
    if not soundboard_cog:
        await interaction.followup.send("❌ **Soundboard modülü yüklenmemiş!**")
        return

    ctx = await bot.get_context(interaction)
    await ctx.invoke(soundboard_cog.play_sound, sound_name=sound_name)

@bot.tree.command(name="speak", description="Botun yazdığınız metni sesli okumasını sağlar.")
async def slash_speak(interaction: discord.Interaction, mesaj: str):
    await interaction.response.defer()

    if interaction.user.voice and interaction.user.voice.channel:
        kanal = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if not voice_client:
            voice_client = await kanal.connect()

        print("📝 Metin alındı: ", mesaj)

        print("🎙 Ses dosyası oluşturuluyor...")
        ses_dosyasi = await metni_sese_cevir(mesaj)
        ses_dosyasi = os.path.abspath(ses_dosyasi)
        print(f"📂 Ses dosyası kaydedildi: {ses_dosyasi}")

        FFMPEG_PATH = "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"
        ffmpeg_options = {
            'before_options': '-nostats',
            'options': '-vn'
        }

        try:
            print("🔊 FFmpeg ile ses oynatılıyor...")
            source = discord.FFmpegPCMAudio(ses_dosyasi, executable=FFMPEG_PATH, **ffmpeg_options)

            async with bot.audio_lock:
                voice_client.play(source, after=lambda e: print(
                    f"✅ Ses başarıyla çalındı." if not e else f"❌ FFmpeg Hata: {e}"))

            await interaction.followup.send(f"🔊 **Bot yazdığınızı okuyor...**")

        except Exception as e:
            await interaction.followup.send(f"❌ **Ses çalınırken hata oluştu:** {e}")
            print(f"FFmpeg Hata: {e}")

    else:
        await interaction.followup.send("Önce bir ses kanalına gir! 🎤")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    message_id = payload.message_id
    if message_id not in bot.music_messages:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    channel = guild.get_channel(bot.music_messages[message_id])
    if not channel:
        return

    message = await channel.fetch_message(message_id)
    user = guild.get_member(payload.user_id)
    voice_client = guild.voice_client

    if not voice_client or not voice_client.is_connected():
        await message.reply("❌ **Bot bir ses kanalında değil!**")
        return

    emoji = str(payload.emoji)

    ctx = await bot.get_context(message)

    if emoji == "⏪":
        if bot.queue:
            if bot.currently_playing:
                bot.queue.insert(0, bot.currently_playing)
            await play_next(ctx)

    elif emoji == "⏸":
        if voice_client.is_playing():
            voice_client.pause()
            await message.reply("⏸ **Şarkı duraklatıldı!**")

    elif emoji == "▶":
        if voice_client.is_paused():
            voice_client.resume()
            await message.reply("▶ **Şarkı devam ediyor!**")

    elif emoji == "⏩":  # Sonraki şarkıya geç
        await play_next(ctx)

    elif emoji == "⏹":  # Durdur
        voice_client.stop()
        bot.queue = []
        await message.reply("⏹ **Şarkı durduruldu ve kuyruk temizlendi!**")

    await message.remove_reaction(emoji, user)

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def gemini_cevap(mesaj: str) -> str:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(mesaj)
        return response.text

    async def metni_sese_cevir(self, metin: str, dosya_adi="cevap.mp3"):
        try:
            print("🔄 Edge TTS ile ses dönüştürülüyor...")

            tts = edge_tts.Communicate(metin, voice="tr-TR-AhmetNeural")
            await tts.save(dosya_adi)

            print("✅ Ses dosyası başarıyla oluşturuldu. İşlem tamamlandı.")

            audio = AudioSegment.from_mp3(dosya_adi)
            audio = audio.set_frame_rate(44100).set_channels(2)
            audio.export(dosya_adi, format="mp3", bitrate="192k")

            print(f"📂 Kaydedilen ses dosyası: {dosya_adi}")
            return dosya_adi

        except Exception as e:
            print(f"❌ Ses dosyası oluşturulurken hata oluştu: {e}")
            return None

    @commands.command()
    async def ai(self, ctx, *, mesaj: str):
        await ctx.send(f"🐶 **TACİ:** {self.gemini_cevap(mesaj)}")

    @commands.command()
    async def ask(self, ctx, *, mesaj: str):
        if ctx.author.voice and ctx.author.voice.channel:
            kanal = ctx.author.voice.channel
            if not ctx.voice_client:
                await kanal.connect()

            print("🟢 AI'ye mesaj gönderiliyor...")
            cevap = self.gemini_cevap(mesaj)
            print(f"📩 AI'den gelen cevap: {cevap}")

            print("🎙 Ses dosyası oluşturuluyor...")
            ses_dosyasi = await self.metni_sese_cevir(cevap)
            ses_dosyasi = os.path.abspath(ses_dosyasi)
            print(f"📂 Ses dosyası kaydedildi: {ses_dosyasi}")

            FFMPEG_PATH = "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"
            ffmpeg_options = {
                'before_options': '-nostats',
                'options': '-vn'
            }

            try:
                print("🔊 FFmpeg ile ses oynatılıyor...")
                source = discord.FFmpegPCMAudio(ses_dosyasi, executable=FFMPEG_PATH, **ffmpeg_options)

                async with self.bot.audio_lock:
                    ctx.voice_client.play(source, after=lambda e: print(
                        f"✅ Ses başarıyla çalındı." if not e else f"❌ FFmpeg Hata: {e}"))

                await ctx.send(f"🔊 **Sesli yanıt veriliyor...**")

            except Exception as e:
                await ctx.send(f"❌ **Ses çalınırken hata oluştu:** {e}")
                print(f"FFmpeg Hata: {e}")

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
            voice_client = interaction.guild.voice_client

            if not voice_client:
                voice_client = await kanal.connect()

            print("🟢 AI'ye mesaj gönderiliyor...")
            cevap = self.gemini_cevap(mesaj)
            print(f"📩 AI'den gelen cevap: {cevap}")

            print("🎙 Ses dosyası oluşturuluyor...")
            ses_dosyasi = await self.metni_sese_cevir(cevap)
            ses_dosyasi = os.path.abspath(ses_dosyasi)
            print(f"📂 Ses dosyası kaydedildi: {ses_dosyasi}")

            FFMPEG_PATH = "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"
            ffmpeg_options = {
                'before_options': '-nostats',
                'options': '-vn'
            }

            try:
                print("🔊 FFmpeg ile ses oynatılıyor...")
                source = discord.FFmpegPCMAudio(ses_dosyasi, executable=FFMPEG_PATH, **ffmpeg_options)

                async with self.bot.audio_lock:
                    voice_client.play(source, after=lambda e: print(
                        f"✅ Ses başarıyla çalındı." if not e else f"❌ FFmpeg Hata: {e}"))

                await interaction.followup.send(f"🔊 **Sesli yanıt veriliyor...**")

            except Exception as e:
                await interaction.followup.send(f"❌ **Ses çalınırken hata oluştu:** {e}")
                print(f"FFmpeg Hata: {e}")

        else:
            await interaction.followup.send("Önce bir ses kanalına gir! 🎤")


async def setup(bot):
    await bot.add_cog(AIChat(bot))
    await bot.add_cog(Music(bot))
    await bot.add_cog(WelcomeSound(bot))
    await bot.add_cog(TwitterNews(bot))
    await soundboard_setup(bot)
    await bot.add_cog(LonerBully(bot))

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

### Help Komutu ###
@bot.tree.command(name="help", description="Bot komutlarını gösterir")
async def help_command(interaction: discord.Interaction):
    help_message = """
    **Bot Komutları**:

    **Müzik Komutları:**
    `/play <şarkı_adı>` - Şarkı çalar
    `/skip` - Şarkıyı atlar
    `/pause` - Şarkıyı duraklatır
    `/resume` - Duraklatılmış şarkıyı devam ettirir
    `/queue` - Kuyruğu gösterir
    `/clear` - Kuyruğu temizler
    `/nowplaying` - Şu an çalan şarkıyı gösterir
    `/volume <seviye>` - Botun ses seviyesini ayarlar

    **Soundboard Komutları:**
    `/play_sound <ses_adı>` - Belirtilen ses efektini çalar

    **Moderasyon Komutları:**
    `/kick <kullanıcı>` - Kullanıcıyı sunucudan atar
    `/ban <kullanıcı>` - Kullanıcıyı sunucudan yasaklar

    **Eğlence Komutları:**
    `/roll` - Zar atar
    `/meme` - Rastgele bir meme gönderir -Güncellenecek
    """
    await interaction.response.send_message(content=help_message)

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