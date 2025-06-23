from discord import Status, Activity, ActivityType
from discord.ext import tasks
import random

STATUSES = [
    Activity(type=ActivityType.watching, name="Musti'nin mangalını"),
    Activity(type=ActivityType.listening, name="Mia'nın bağırmalarını"),
    Activity(type=ActivityType.playing, name="Fat Belly Bastard'ın ayağıyla"),
    Activity(type=ActivityType.watching, name="Nurettin ile Taxi Driver"),
    Activity(type=ActivityType.listening, name="Chieff'in babalara sövmesini"),
    Activity(type=ActivityType.listening, name="Kryjeolas'ın toplantısını"),
    Activity(type=ActivityType.watching, name="Milkmemaybe'nin ekranını"),
    Activity(type=ActivityType.watching, name="Dollysheep'in storylerini"),
    Activity(type=ActivityType.playing, name="Çardak Simulator 2025"),
]

@tasks.loop(minutes=30)
async def cycle_status(bot):
    activity = random.choice(STATUSES)
    await bot.change_presence(status=Status.online, activity=activity)
    print(f"🔁 TACİ'nin yeni durumu: {activity.name}")
