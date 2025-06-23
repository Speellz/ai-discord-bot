import discord
from discord.ext import commands
import random

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roll(self, ctx):
        number = random.randint(1, 6)
        await ctx.send(f"🎲 Zar attın ve {number} geldi!")

    @commands.command()
    async def meme(self, ctx):
        memes = ["https://i.redd.it/lmqy3qkz8li41.jpg", "https://i.redd.it/dtk7w1gkmlj61.jpg"]
        await ctx.send(random.choice(memes))

async def setup(bot):
    await bot.add_cog(Fun(bot))
