import discord
from discord.ext import commands
import os


class Soundboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sounds = {}
        self.load_sounds()

    def load_sounds(self):
        sound_folder = "data/sounds"
        for filename in os.listdir(sound_folder):
            if filename.endswith(".mp3"):
                sound_name = os.path.splitext(filename)[0].lower()
                self.sounds[sound_name] = os.path.join(sound_folder, filename)


    async def ensure_voice(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if ctx.voice_client is None:
                await channel.connect()
            elif ctx.voice_client.channel != channel:
                await ctx.voice_client.move_to(channel)
            return True
        else:
            await ctx.send("❌ **Önce bir ses kanalına gir!**")
            return False

    @commands.command()
    async def play_sound(self, ctx, *, sound_name):
        """Soundboard'dan belirlenen sesi çalar."""
        if sound_name.lower() in self.sounds:
            sound_path = self.sounds[sound_name.lower()]
            if os.path.exists(sound_path):
                if await self.ensure_voice(ctx):  # Bağlantıyı doğrula
                    ctx.voice_client.stop()
                    source = discord.FFmpegPCMAudio(sound_path)
                    ctx.voice_client.play(discord.PCMVolumeTransformer(source, volume=0.5))  # Ses seviyesi ekledim
                    await ctx.send(f"🔊 **{sound_name}** sesi çalınıyor!")
            else:
                await ctx.send("❌ **Bu ses dosyası bulunamadı.**")
        else:
            await ctx.send("❌ **Bu isimde bir ses yok!**")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Eğer mesaj bir soundboard komutuysa, otomatik olarak sesi çalar."""
        if message.author == self.bot.user:
            return

        content = message.content.lower()
        if content in self.sounds:
            ctx = await self.bot.get_context(message)
            await self.play_sound(ctx, sound_name=content)


async def setup(bot):
    await bot.add_cog(Soundboard(bot))
