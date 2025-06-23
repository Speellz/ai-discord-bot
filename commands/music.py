import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []  # Kuyruk
        self.currently_playing = None  # Şu an çalan şarkı
        self.default_sound = "data/sounds/havhav.mp3"  # Varsayılan ses
        self.user_sounds = {}  # Kullanıcıya özel giriş sesleri

    @commands.command()
    async def join(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if ctx.voice_client is None:
                vc = await channel.connect()
                sound_path = self.user_sounds.get(ctx.author.id, self.default_sound)
                if os.path.exists(sound_path):
                    source = discord.FFmpegPCMAudio(sound_path)
                    vc.play(source)

                await ctx.send(f"🔊 **{channel.name}** kanalına bağlandım!")
            else:
                await ctx.send("Ben zaten bir ses kanalındayım!")
        else:
            await ctx.send("Önce bir ses kanalına gir!")

    @commands.command()
    async def leave(self, ctx):
        """Botu ses kanalından çıkarır ve kuyruğu temizler."""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            self.queue.clear()
            await ctx.send("🔇 Kanaldan ayrıldım ve kuyruğu temizledim!")
        else:
            await ctx.send("Ben zaten bir ses kanalında değilim!")

    @commands.command()
    async def play(self, ctx, *, url_or_search):
        """Tek şarkı çalma, playlist çalma, veya şarkı arama"""
        if not ctx.voice_client:
            await ctx.invoke(self.join)  # Bot bağlı değilse bağlan

        # Playlist URL'si mi yoksa şarkı adı mı kontrol et
        if "playlist" in url_or_search:  # Eğer playlist URL'si verilmişse
            await self.play_playlist(ctx, url_or_search)
            return
        elif url_or_search.startswith("http"):  # Eğer URL verilmişse
            url = url_or_search
        else:  # Şarkı adı verilmişse
            search_url = f"ytsearch:{url_or_search}"
            ydl_opts = {
                'format': 'bestaudio/best',  # Audio-only format
                'quiet': True,
                'noplaylist': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                url = info['entries'][0]['url']  # İlk sonucu al
                await ctx.send(f"🎶 **Şarkı Bulundu:** {info['entries'][0]['title']}")

        # Şarkıyı çal
        await self.start_playing(ctx, url)

    async def play_playlist(self, ctx, url):
        """YouTube playlist’ini çalar."""
        ydl_opts = {
            'format': 'bestaudio/best',  # Audio-only format
            'quiet': True,
            'extract_flat': True,  # Playlist'in sadece linklerini al
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist = ydl.extract_info(url, download=False)
            for entry in playlist['entries']:
                await self.play(ctx, url=entry['url'])  # Her şarkıyı sırayla çal

    async def start_playing(self, ctx, url):
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'cookiefile': 'cookies.txt'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['url']
            title = info['title']

        try:
            ffmpeg_options = {
                'before_options': "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                'options': '-vn'
            }
            source = discord.FFmpegPCMAudio(url2, **ffmpeg_options)
            ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
            await ctx.send(f"🎶 **Şimdi Çalıyor:** {title}")
        except Exception as e:
            await ctx.send(f"🚨 **Şarkı başlatılamadı!** Hata: {str(e)}")

    async def play_next(self, ctx):
        """Sıradaki şarkıyı çalar."""
        if len(self.queue) > 0:
            next_url, next_title = self.queue.pop(0)
            await self.start_playing(ctx, next_url, next_title)
        else:
            self.currently_playing = None  # Kuyruk boşaldıysa sıfırla

    @commands.command()
    async def skip(self, ctx):
        """Şu anki şarkıyı atlayıp sıradakini çalar."""
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()  # Şarkıyı durdur
            await ctx.send("⏭ **Şarkı geçildi!**")
        else:
            await ctx.send("Şu anda çalan bir şarkı yok!")

    @commands.command()
    async def pause(self, ctx):
        """Şarkıyı duraklatır."""
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("⏸ **Şarkı duraklatıldı!**")
        else:
            await ctx.send("Şu anda çalan bir şarkı yok!")

    @commands.command()
    async def resume(self, ctx):
        """Duraklatılmış şarkıyı devam ettirir."""
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("▶ **Şarkı devam ediyor!**")
        else:
            await ctx.send("Duraklatılmış bir şarkı yok!")

    @commands.command()
    async def clear(self, ctx):
        """Kuyruğu temizler."""
        self.queue.clear()
        await ctx.send("🗑 **Müzik kuyruğu temizlendi!**")

    @commands.command()
    async def nowplaying(self, ctx):
        """Şu an çalan şarkının bilgisini gösterir."""
        if self.currently_playing:
            await ctx.send(f"🎶 **Şu anda çalan şarkı:** {self.currently_playing}")
        else:
            await ctx.send("Şu anda çalan bir şarkı yok!")

    @commands.command()
    async def volume(self, ctx, volume: int):
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source, volume=volume / 100)
            await ctx.send(f"🔊 **Ses seviyesi** {volume}% olarak ayarlandı!")
        else:
            await ctx.send("Ben bir ses kanalında değilim!")

    @commands.command()
    async def queue(self, ctx):
        """Kuyruğun şu anki durumunu gösterir."""
        if len(self.queue) > 0:
            queue_list = "\n".join([f"{idx + 1}. {title}" for idx, (url, title) in enumerate(self.queue)])
            await ctx.send(f"📋 **Şu anki kuyruk:**\n{queue_list}")
        else:
            await ctx.send("🛑 **Kuyruk boş!**")

    @commands.command()
    async def remove(self, ctx, index: int):
        """Kuyruktan şarkı kaldırır."""
        try:
            removed_song = self.queue.pop(index - 1)
            await ctx.send(f"❌ **Kaldırıldı:** {removed_song[1]}")
        except IndexError:
            await ctx.send(f"❌ **Geçersiz numara**: Kuyrukta {len(self.queue)} şarkı bulunuyor!")


async def setup(bot):
    await bot.add_cog(Music(bot))
