from discord.ext import commands, tasks
import aiohttp
import xml.etree.ElementTree as ET
import discord
import os
import json

KOERI_XML_URL = "http://udim.koeri.boun.edu.tr/zeqmap/xmlt.asp"
CHANNEL_ID = 1364910252675305582
HISTORY_FILE = "koeri_history.json"

class KoeriQuakeNotifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sent_quakes = self.load_history()
        self.task_started = False

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def save_history(self):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(self.sent_quakes), f, ensure_ascii=False, indent=2)

    async def fetch_quakes(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(KOERI_XML_URL) as response:
                    data = await response.text()
                    return ET.fromstring(data)
        except Exception as e:
            print(f"❌ KOERI verisi alınamadı: {e}")
            return None

    @tasks.loop(minutes=2)
    async def check_quakes(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(CHANNEL_ID)
        root = await self.fetch_quakes()
        if root is None:
            return

        for eq in root.findall("eq"):
            date = eq.find("date").text.strip()
            region = eq.find("region").text.strip()
            ml = eq.find("ml").text.strip()
            key = f"{date}-{region}-{ml}"

            if key in self.sent_quakes:
                continue

            self.sent_quakes.add(key)
            self.save_history()

            embed = discord.Embed(title="📢 Yeni Deprem (KOERI)", color=0xE74C3C)
            embed.add_field(name="Tarih", value=date, inline=True)
            embed.add_field(name="Bölge", value=region, inline=True)
            embed.add_field(name="Büyüklük (ML)", value=ml, inline=True)
            embed.add_field(name="Derinlik", value=eq.find("depth").text.strip() + " km", inline=True)
            embed.add_field(name="Konum", value=f"Lat: {eq.find('latitude').text.strip()}, Lon: {eq.find('longitude').text.strip()}", inline=False)

            await channel.send(embed=embed)
            print(f"🌍 Yeni deprem bildirildi: {region} - {ml} - {date}")

    async def start_task(self):
        if not self.task_started:
            self.check_quakes.start()
            self.task_started = True

    def cog_unload(self):
        self.check_quakes.cancel()
        print("🛑 KOERI takip durduruldu.")
