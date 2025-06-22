import os
import feedparser
import discord
from discord.ext import commands, tasks

QUAKE_FEED = "https://www.emsc-csem.org/service/rss/rss.php?typ=emsc&min_mag=4"
CHECK_INTERVAL = 10  # minutes
QUAKE_CHANNEL_ID = int(os.getenv("QUAKE_CHANNEL_ID", 0))


class QuakeNotifier(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.latest_id: str | None = None
        if QUAKE_CHANNEL_ID:
            self.check_quakes.start()

    def fetch_latest(self):
        feed = feedparser.parse(QUAKE_FEED)
        if not feed.entries:
            return None
        return feed.entries[0]

    @tasks.loop(minutes=CHECK_INTERVAL)
    async def check_quakes(self):
        await self.bot.wait_until_ready()
        entry = self.fetch_latest()
        if not entry:
            return
        if self.latest_id == entry.id:
            return
        self.latest_id = entry.id
        channel = self.bot.get_channel(QUAKE_CHANNEL_ID)
        if channel:
            await channel.send(f"🌎 **Earthquake:** {entry.title}\n{entry.link}")

async def setup(bot: commands.Bot):
    await bot.add_cog(QuakeNotifier(bot))
