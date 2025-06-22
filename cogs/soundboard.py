import os
import discord
from discord import app_commands
from discord.ext import commands

class Soundboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sounds = {}
        self.load_sounds()

    def load_sounds(self):
        folder = "data/sounds"
        if not os.path.isdir(folder):
            return
        for fn in os.listdir(folder):
            if fn.endswith(".mp3"):
                self.sounds[fn[:-4].lower()] = os.path.join(folder, fn)

    async def ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
            if not interaction.guild.voice_client:
                return await channel.connect()
            return interaction.guild.voice_client
        await interaction.followup.send("Ses kanalına gir", ephemeral=True)
        return None

    @app_commands.command(description="Belirtilen sesi çalar")
    async def play_sound(self, interaction: discord.Interaction, sound_name: str):
        await interaction.response.defer()
        vc = await self.ensure_voice(interaction)
        if not vc:
            return
        path = self.sounds.get(sound_name.lower())
        if not path or not os.path.exists(path):
            await interaction.followup.send("Ses bulunamadı")
            return
        source = discord.FFmpegPCMAudio(path)
        vc.stop()
        vc.play(source)
        await interaction.followup.send(f"Çalıyor: {sound_name}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Soundboard(bot))
