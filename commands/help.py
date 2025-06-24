import discord
from discord.ext import commands
from discord import app_commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Bot komutlarını gösterir")
    async def help_command(self, interaction: discord.Interaction):
        help_message = """
**🎵 Müzik Komutları:**
`/play <şarkı_adı>` – Şarkı çalar  
`/skip` – Şarkıyı atlar  
`/pause` – Şarkıyı duraklatır  
`/resume` – Duraklatılan şarkıyı devam ettirir  
`/queue` – Şarkı kuyruğunu gösterir  
`/clear` – Kuyruğu temizler  
`/nowplaying` – Şu an çalan şarkıyı gösterir  
`/volume <seviye>` – Ses seviyesini ayarlar  

**🔊 Soundboard Komutları:**
`/play_sound <ses_adı>` – Belirtilen sesi çalar  

**🧠 Yapay Zeka:**
`/ai <mesaj>` – Sohbet eder  
`/ask <mesaj>` – Mesajı sesli yanıtlar  

**🌍 Deprem Bilgisi:**
`/emsc` – Son 10 Türkiye depremini listeler  

**🎙️ Ses Kontrol:**
`/join` – Botu ses kanalına sokar  
`/leave` – Botu ses kanalından çıkarır  
`/speak <mesaj>` – Yazdığını sesli okur  

**🔨 Moderasyon:**
`/kick <kullanıcı>` – Sunucudan atar  
`/ban <kullanıcı>` – Yasaklar  

**🎲 Eğlence:**
`/roll` – Zar atar  
`/meme` – Rastgele meme gönderir *(yakında)*
"""
        await interaction.response.send_message(help_message)
