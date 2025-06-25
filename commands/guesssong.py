import os
import random
import datetime
import discord
import yt_dlp
from discord.ext import commands
from discord import app_commands

with open("data/song_list.txt", "r", encoding="utf-8") as f:
    SONG_POOL = [line.strip() for line in f if line.strip()]


TEMP_FILE = "data/guess_temp.mp3"
guess_sessions = {}  # guild_id -> session dict
guess_scores = {}    # user_id -> score
guess_history = {}   # guild_id -> list of used songs

class GuessSong(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_unused_song(self, guild_id):
        used = guess_history.get(guild_id, [])
        remaining = list(set(SONG_POOL) - set(used))
        if not remaining:
            guess_history[guild_id] = []
            remaining = SONG_POOL[:]
        song = random.choice(remaining)
        guess_history.setdefault(guild_id, []).append(song)
        return song

    async def play_next_song(self, guild, channel, voice_user):
        query = self.get_unused_song(guild.id)
        filename = TEMP_FILE

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'outtmpl': 'data/guess_temp.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }]
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"ytsearch1:{query}"])
        except Exception as e:
            await channel.send(f"❌ Şarkı indirilemedi: {e}")
            return

        if not os.path.exists(filename):
            await channel.send("❌ MP3 dosyası oluşturulamadı.")
            return

        voice_channel = voice_user.voice.channel
        voice_client = guild.voice_client or await voice_channel.connect()

        if voice_client.is_playing():
            voice_client.stop()

        ffmpeg_options = {
            'before_options': '-ss 00:00:00 -t 5',
            'options': '-vn'
        }

        source = discord.FFmpegPCMAudio(filename, **ffmpeg_options)
        voice_client.play(source)

        embed = discord.Embed(title="🎵 Tahmin Et!", description="5 saniyelik şarkı çalındı. Mesaj yazarak tahmin et!", color=discord.Color.green())
        message = await channel.send(embed=embed)
        await message.add_reaction("❌")
        await message.add_reaction("💡")
        await message.add_reaction("📊")
        await message.add_reaction("🔁")

        guess_sessions[guild.id] = {
            "answer": query,
            "channel_id": channel.id,
            "filename": filename,
            "message_id": message.id,
            "start_time": datetime.datetime.utcnow(),
            "user": voice_user
        }

    @app_commands.command(name="guess_song", description="Şarkıyı tahmin et oyununu başlatır")
    async def guess_song(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("🎤 Önce bir ses kanalına gir!")
            return

        await self.play_next_song(interaction.guild, interaction.channel, interaction.user)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        session = guess_sessions.get(payload.guild_id)
        if not session or payload.message_id != session["message_id"]:
            return

        channel = self.bot.get_channel(session["channel_id"])
        if not channel:
            return

        emoji = str(payload.emoji)
        user = self.bot.get_user(payload.user_id)

        if emoji == "❌":
            await channel.send("❌ Oyun sonlandırıldı.")
            if os.path.exists(session["filename"]):
                os.remove(session["filename"])
            guess_sessions.pop(payload.guild_id, None)

        elif emoji == "💡":
            ipucu = session["answer"][0].upper()
            await channel.send(f"💡 İpucu: Şarkı şu harfle başlıyor: **{ipucu}**")

        elif emoji == "🔁":
            voice_client = channel.guild.voice_client
            if voice_client and os.path.exists(session["filename"]):
                if voice_client.is_playing():
                    voice_client.stop()

                ffmpeg_options = {
                    'before_options': '-ss 00:00:00 -t 5',
                    'options': '-vn'
                }

                source = discord.FFmpegPCMAudio(session["filename"], **ffmpeg_options)
                voice_client.play(source)
                await channel.send("🔁 Şarkı tekrar çalınıyor...")
            else:
                await channel.send("❗ Ses dosyası yok ya da bot kanalda değil.")

        elif emoji == "📊":
            if not guess_scores:
                await channel.send("📊 Henüz kimse puan kazanmadı!")
                return
            sorted_scores = sorted(guess_scores.items(), key=lambda x: x[1], reverse=True)
            lines = [f"<@{uid}>: {score}" for uid, score in sorted_scores]
            await channel.send("🏆 **Skor Tablosu:**\n" + "\n".join(lines))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        session = guess_sessions.get(message.guild.id)
        if not session or message.channel.id != session["channel_id"]:
            return

        if session["answer"].lower() in message.content.lower():
            user_id = message.author.id
            guess_scores[user_id] = guess_scores.get(user_id, 0) + 1

            await message.channel.send(f"🎉 Doğru cevap {message.author.mention}! Şarkı: **{session['answer']}**\n🏆 Skorun: **{guess_scores[user_id]}**")

            if os.path.exists(session["filename"]):
                os.remove(session["filename"])

            await self.play_next_song(message.guild, message.channel, message.author)
        else:
            await message.channel.send(f"❌ Yanlış tahmin {message.author.mention}! Tekrar dene.")


async def setup(bot):
    await bot.add_cog(GuessSong(bot))
