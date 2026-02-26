import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger('thronos_bot.announcements')

class Announcements(commands.Cog):
    """Manage announcements from website or manual posts."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="announce", description="Post announcement (Admin only)")
    @commands.has_permissions(administrator=True)
    async def announce_command(self, ctx: commands.Context, *, message: str):
        """Post an announcement to the announcements channel."""
        announcements_channel = discord.utils.get(ctx.guild.text_channels, name="announcements")
        
        if not announcements_channel:
            await ctx.reply("❌ Announcements channel not found.", ephemeral=True)
            return
        
        # Create rich embed
        embed = discord.Embed(
            title="📢 Official Announcement",
            description=message,
            color=0xf39c12
        )
        embed.set_footer(text=f"Posted by {ctx.author.display_name}")
        embed.timestamp = discord.utils.utcnow()
        
        await announcements_channel.send(embed=embed)
        await ctx.reply("✅ Announcement posted!", ephemeral=True)
        logger.info(f"{ctx.author} posted announcement: {message[:50]}")

async def setup(bot):
    await bot.add_cog(Announcements(bot))
