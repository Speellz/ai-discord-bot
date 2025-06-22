import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queue: list[tuple[str, str]] = []
        self.current: str | None = None
        self.music_messages: dict[int, int] = {}
        self.audio_lock = asyncio.Lock()

    async def ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
            if not interaction.guild.voice_client:
                return await channel.connect()
            return interaction.guild.voice_client
        await interaction.followup.send("Önce bir ses kanalına gir!", ephemeral=True)
        return None

    async def start_playing(self, interaction: discord.Interaction, url: str, title: str):
        vc = interaction.guild.voice_client
        if not vc:
            return
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        source = discord.FFmpegPCMAudio(url, **ffmpeg_options)

        def after(_):
            asyncio.run_coroutine_threadsafe(self.play_next(interaction), self.bot.loop)

        async with self.audio_lock:
            vc.play(source, after=after)
        self.current = title
        embed = discord.Embed(title="Şimdi Çalıyor", description=title)
        message = await interaction.followup.send(embed=embed)
        for emoji in ["⏪", "⏸", "▶", "⏩", "⏹"]:
            await message.add_reaction(emoji)
        self.music_messages[message.id] = interaction.channel.id

    async def play_next(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc:
            return
        if self.queue:
            url, title = self.queue.pop(0)
            await self.start_playing(interaction, url, title)
        else:
            self.current = None

    @app_commands.command(description="Şarkı çalar")
    async def play(self, interaction: discord.Interaction, *, query: str):
        print(f"/play invoked by {interaction.user} with query: {query}")
        await interaction.response.defer()
        vc = await self.ensure_voice(interaction)
        if not vc:
            return
        ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}" if not query.startswith("http") else query, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            url = info['url']
            title = info['title']
        if vc.is_playing() or vc.is_paused():
            self.queue.append((url, title))
            await interaction.followup.send(f"Sıraya eklendi: {title}")
        else:
            await self.start_playing(interaction, url, title)

    @app_commands.command(description="Şarkıyı atlar")
    async def skip(self, interaction: discord.Interaction):
        print(f"/skip invoked by {interaction.user}")
        await interaction.response.defer()
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.followup.send("Şarkı geçildi")
        else:
            await interaction.followup.send("Çalan şarkı yok")

    @app_commands.command(description="Şarkıyı duraklatır")
    async def pause(self, interaction: discord.Interaction):
        print(f"/pause invoked by {interaction.user}")
        await interaction.response.defer()
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.followup.send("Duraklatıldı")
        else:
            await interaction.followup.send("Şarkı çalmıyor")

    @app_commands.command(description="Duraklatılan şarkıyı sürdürür")
    async def resume(self, interaction: discord.Interaction):
        print(f"/resume invoked by {interaction.user}")
        await interaction.response.defer()
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.followup.send("Devam ediyor")
        else:
            await interaction.followup.send("Duraklatılmış şarkı yok")

    @app_commands.command(description="Müzik kuyruğunu gösterir")
    async def queue(self, interaction: discord.Interaction):
        print(f"/queue invoked by {interaction.user}")
        lines = [f"{i+1}. {title}" for i, (_, title) in enumerate(self.queue)]
        text = "\n".join(lines) if lines else "Kuyruk boş"
        await interaction.response.send_message(text)

    @app_commands.command(description="Kuyruktan şarkı kaldırır")
    async def remove(self, interaction: discord.Interaction, index: int):
        print(f"/remove invoked by {interaction.user} index: {index}")
        if 0 < index <= len(self.queue):
            _, title = self.queue.pop(index-1)
            await interaction.response.send_message(f"Kaldırıldı: {title}")
        else:
            await interaction.response.send_message("Geçersiz sıra numarası")

    @app_commands.command(description="Botu ses kanalına sokar")
    async def join(self, interaction: discord.Interaction):
        print(f"/join invoked by {interaction.user}")
        await interaction.response.defer()
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
            if not interaction.guild.voice_client:
                await channel.connect()
            await interaction.followup.send(f"{channel.name} kanalına bağlandım")
        else:
            await interaction.followup.send("Ses kanalına gir")

    @app_commands.command(description="Botu ses kanalından çıkarır")
    async def leave(self, interaction: discord.Interaction):
        print(f"/leave invoked by {interaction.user}")
        await interaction.response.defer()
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            self.queue.clear()
            await interaction.followup.send("Kanaldan ayrıldım")
        else:
            await interaction.followup.send("Bir kanalda değilim")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        print(f"Reaction {payload.emoji} added by {payload.user_id}")
        if payload.user_id == self.bot.user.id:
            return
        if payload.message_id not in self.music_messages:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(self.music_messages[payload.message_id])
        if not channel:
            return
        message = await channel.fetch_message(payload.message_id)
        vc = guild.voice_client
        if not vc:
            return
        emoji = str(payload.emoji)
        if emoji == "⏭":
            vc.stop()
        elif emoji == "⏸" and vc.is_playing():
            vc.pause()
        elif emoji == "▶" and vc.is_paused():
            vc.resume()
        elif emoji == "⏹":
            vc.stop()
            self.queue.clear()
        await message.remove_reaction(payload.emoji, discord.Object(id=payload.user_id))

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
