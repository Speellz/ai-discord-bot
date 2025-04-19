import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="Sebep belirtilmedi"):
        await member.kick(reason=reason)
        await ctx.send(f"{member.mention} sunucudan atıldı! 🚪")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="Sebep belirtilmedi"):
        await member.ban(reason=reason)
        await ctx.send(f"{member.mention} sunucudan yasaklandı! 🔨")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
