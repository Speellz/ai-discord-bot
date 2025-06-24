import discord
import asyncio
import yt_dlp
import os
import uuid
import shutil
from discord.ext import commands, tasks
from discord import app_commands

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.music_messages = {}
        self.currently_playing = None
        self.previous_tracks = []
        self.disconnect_timer = {}  # guild_id -> asyncio.Task
        self.last_channel_id = {}   # guild_id -> last interaction channel

    @app_commands.command(name="play", description="Şarkı çalar (indirip oynatır)")
    async def slash_play(self, interaction: discord.Interaction, song: str):
        await interaction.response.defer()

        voice_client = interaction.guild.voice_client
        if not voice_client:
            if interaction.user.voice:
                channel = interaction.user.voice.channel
                voice_client = await channel.connect()
            else:
                await interaction.followup.send("\u00d6nce bir ses kanalına gir!")
                return

        self.last_channel_id[interaction.guild.id] = interaction.channel.id

        temp_id = str(uuid.uuid4())
        output_path = f"downloads/{temp_id}.%(ext)s"
        final_path = f"downloads/{temp_id}.mp3"

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'default_search': 'ytsearch',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(song, download=True)
                title = info.get('title', 'Bilinmeyen Başlık')

            if not os.path.exists(final_path):
                await interaction.followup.send("❌ Şarkı indirilemedi.")
                return

            if voice_client.is_playing() or voice_client.is_paused():
                self.queue.append((final_path, title))
                await interaction.followup.send(f"**Sıraya eklendi:** {title}")
            else:
                await self.start_playing(interaction.guild, final_path, title)

        except Exception as e:
            await interaction.followup.send(f"❌ Hata oluştu: {e}")
            print(f"[play] YDL Hata: {e}")

    async def start_playing(self, guild, file_path, title):
        voice_client = guild.voice_client
        source = discord.FFmpegPCMAudio(file_path)

        def after_playing(error):
            self.previous_tracks.append((file_path, title))
            if error:
                print(f"FFmpeg Hata: {error}")
            asyncio.run_coroutine_threadsafe(self.play_next(guild), self.bot.loop)

        voice_client.play(source, after=after_playing)
        self.currently_playing = (file_path, title)

        channel = self.bot.get_channel(self.last_channel_id[guild.id])
        if channel:
            embed = discord.Embed(title="🎶 Şimdi Çalıyor:", description=f"**{title}**", color=discord.Color.green())
            message = await channel.send(embed=embed)
            for emoji in ["⏪", "⏸", "▶", "⏭", "⏹"]:
                await message.add_reaction(emoji)
            self.music_messages[message.id] = channel.id

        self.reset_disconnect_timer(guild.id)

    async def play_next(self, guild):
        voice_client = guild.voice_client

        if self.queue:
            # Şu anki şarkıyı previous'a kaydet
            if self.currently_playing:
                self.previous_tracks.append(self.currently_playing)

            next_file, next_title = self.queue.pop(0)
            self.currently_playing = (next_file, next_title)
            source = discord.FFmpegPCMAudio(next_file)

            def after_playing(error):
                if error:
                    print(f"FFmpeg Hata: {error}")
                try:
                    os.remove(next_file)
                except Exception as e:
                    print(f"⚠️ Silinemedi: {e}")
                asyncio.run_coroutine_threadsafe(self.play_next(guild), self.bot.loop)

            voice_client.stop()
            voice_client.play(source, after=after_playing)

            channel = self.bot.get_channel(self.last_channel_id.get(guild.id))
            if channel:
                embed = discord.Embed(title="🎶 Şimdi Çalıyor:", description=f"**{next_title}**",
                                      color=discord.Color.green())
                await channel.send(embed=embed)

        else:
            self.currently_playing = None
            channel = self.bot.get_channel(self.last_channel_id.get(guild.id))
            if channel:
                await channel.send("🎵 **Kuyruktaki tüm şarkılar çalındı!**")
            self.reset_disconnect_timer(guild.id)

    async def play_previous(self, guild):
        voice_client = guild.voice_client

        if self.previous_tracks:
            file_path, title = self.previous_tracks.pop()
            if os.path.exists(file_path):
                if self.currently_playing:
                    self.queue.insert(0, self.currently_playing)
                self.currently_playing = (file_path, title)
                source = discord.FFmpegPCMAudio(file_path)

                def after_playing(error):
                    if error:
                        print(f"FFmpeg Hata: {error}")
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"⚠️ Silinemedi: {e}")
                    asyncio.run_coroutine_threadsafe(self.play_next(guild), self.bot.loop)

                voice_client.stop()
                voice_client.play(source, after=after_playing)

                channel = self.bot.get_channel(self.last_channel_id.get(guild.id))
                if channel:
                    embed = discord.Embed(title="🔁 Önceki Şarkı:", description=f"**{title}**",
                                          color=discord.Color.blurple())
                    await channel.send(embed=embed)
            else:
                channel = self.bot.get_channel(self.last_channel_id.get(guild.id))
                if channel:
                    await channel.send("⚠️ Önceki şarkının dosyası silinmiş.")
        else:
            channel = self.bot.get_channel(self.last_channel_id.get(guild.id))
            if channel:
                await channel.send("⚠️ Önceki şarkı bilgisi yok.")

    def reset_disconnect_timer(self, guild_id):
        if guild_id in self.disconnect_timer:
            self.disconnect_timer[guild_id].cancel()
        self.disconnect_timer[guild_id] = self.bot.loop.create_task(self.disconnect_after_afk(guild_id))

    async def disconnect_after_afk(self, guild_id):
        await asyncio.sleep(180)
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        voice_client = guild.voice_client
        if voice_client and not voice_client.is_playing():
            await voice_client.disconnect()
            print(f"🔌 {guild.name} sunucusundan 3 dakika sessizlik sonrası ayrıldı.")
            await self.cleanup_downloads()

    async def cleanup_downloads(self):
        try:
            for filename in os.listdir("downloads"):
                file_path = os.path.join("downloads", filename)
                os.remove(file_path)
            print("🧹 İndirilen tüm dosyalar temizlendi.")
        except Exception as e:
            print(f"⚠️ Temizlik sırasında hata oluştu: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        message_id = payload.message_id
        if message_id not in self.music_messages:
            return

        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(self.music_messages[message_id])
        message = await channel.fetch_message(message_id)
        user = guild.get_member(payload.user_id)
        voice_client = guild.voice_client

        if not voice_client or not voice_client.is_connected():
            await message.reply("❌ **Bot bir ses kanalında değil!**")
            return

        emoji = str(payload.emoji)

        if emoji == "⏪":
            await self.play_previous(guild)
        elif emoji == "⏸":
            if voice_client.is_playing():
                voice_client.pause()
                await message.reply("⏸ **Şarkı duraklatıldı!**")
        elif emoji == "▶":
            if voice_client.is_paused():
                voice_client.resume()
                await message.reply("▶ **Şarkı devam ediyor!**")
        elif emoji == "⏭":
            await self.play_next(guild)
        elif emoji == "⏹":
            voice_client.stop()
            self.queue.clear()
            await message.reply("⏹ **Şarkı durduruldu ve kuyruk temizlendi!**")

        await message.remove_reaction(emoji, user)
