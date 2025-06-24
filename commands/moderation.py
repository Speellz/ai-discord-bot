import discord
import os
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
GUILD_ID = int(os.getenv("AUTO_ROLE_GUILD_ID"))
ROLE_ID = int(os.getenv("AUTO_ROLE_ID"))

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Yeni gelen üyeye otomatik rol verme
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != GUILD_ID:
            return

        role = member.guild.get_role(ROLE_ID)
        if role:
            try:
                await member.add_roles(role, reason="Yeni üye - otomatik rol ataması")
                print(f"✅ {member} kullanıcısına rol verildi.")
            except discord.Forbidden:
                print(f"❌ {member} kullanıcısına rol verilemedi. Yetki hatası.")
        else:
            print("❌ Belirtilen rol sunucuda bulunamadı.")

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

    @app_commands.command(name="kick", description="Bir kullanıcıyı sunucudan atar")
    @app_commands.checks.has_permissions(kick_members=True)
    async def slash_kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep belirtilmedi"):
        await member.kick(reason=reason)
        await interaction.response.send_message(f"{member.mention} sunucudan atıldı! 🚪")

    @app_commands.command(name="ban", description="Bir kullanıcıyı sunucudan yasaklar")
    @app_commands.checks.has_permissions(ban_members=True)
    async def slash_ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep belirtilmedi"):
        await member.ban(reason=reason)
        await interaction.response.send_message(f"{member.mention} sunucudan yasaklandı! 🔨")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
