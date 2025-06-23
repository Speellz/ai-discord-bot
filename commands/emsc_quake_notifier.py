import aiohttp
import asyncio
import traceback
import os
import json
from discord.ext import commands
import discord
from datetime import datetime, timedelta

class EMSCQuakeNotifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = 1364910252675305582
        self.ping_roles = [752209690548633711, 576890633374007346]
        self.history_file = "emsc_history.json"
        self.sent_ids = self.load_sent_ids()

    def load_sent_ids(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def save_sent_ids(self):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(list(self.sent_ids), f, indent=2)

    async def fetch_data(self, session, url, retries=5):
        for attempt in range(retries):
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        try:
                            return await response.json()
                        except aiohttp.ContentTypeError:
                            text = await response.text()
                            print(f"[EMSC] ❌ JSON beklenirken HTML geldi: {text[:100]}...")
                            return None
                    else:
                        print(f"[EMSC] ⚠️ HTTP {response.status} hatası ({attempt+1}/{retries})")
            except asyncio.TimeoutError:
                print(f"[EMSC] ⏳ Zaman aşımı ({attempt+1}/{retries})")
            except aiohttp.ClientError as e:
                print(f"[EMSC] ❌ Bağlantı hatası: {e}")
            await asyncio.sleep(3)
        print("[EMSC] ❌ Tüm denemeler başarısız oldu.")
        return None

    async def start_task(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(self.channel_id)
        timeout = aiohttp.ClientTimeout(total=10)
        url = "https://www.seismicportal.eu/fdsnws/event/1/query?limit=5&format=json"

        while not self.bot.is_closed():
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    data = await self.fetch_data(session, url)
                    if not data:
                        await asyncio.sleep(7)
                        continue

                    events = data.get("features", [])
                    for event in events:
                        props = event.get("properties", {})
                        region = props.get("flynn_region", "")
                        event_id = event.get("id", "")
                        magnitude = float(props.get("mag", 0))

                        if "TURKEY" not in region.upper():
                            continue
                        if magnitude < 3.0:
                            continue
                        if event_id in self.sent_ids:
                            continue

                        self.sent_ids.add(event_id)
                        self.save_sent_ids()

                        try:
                            utc_time = datetime.strptime(props["time"], "%Y-%m-%dT%H:%M:%S.%fZ")
                        except ValueError:
                            utc_time = datetime.strptime(props["time"], "%Y-%m-%dT%H:%M:%SZ")
                        turkey_time = utc_time + timedelta(hours=3)
                        formatted_time = turkey_time.strftime("%d %B %Y - %H:%M")

                        embed = discord.Embed(
                            title="🌍 Türkiye'de Deprem",
                            description=f"{region}",
                            color=discord.Color.orange()
                        )
                        embed.add_field(name="💥 Büyüklük", value=str(magnitude))
                        embed.add_field(name="🕒 Zaman", value=formatted_time)
                        embed.add_field(name="📏 Derinlik", value=f"{props.get('depth', 'N/A')} km")

                        mention = ""
                        if magnitude >= 3.5:
                            mention = " ".join([f"<@&{role_id}>" for role_id in self.ping_roles])

                        await channel.send(content=mention if mention else None, embed=embed)
                        print(f"📢 Deprem paylaşıldı: {region} - {magnitude}")
                        break

            except Exception:
                print("[EMSC] Hata oluştu:")
                traceback.print_exc()

            await asyncio.sleep(30)
