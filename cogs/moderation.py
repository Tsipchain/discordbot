import discord
from discord.ext import commands
import logging

logger = logging.getLogger('thronos_bot.moderation')

class Moderation(commands.Cog):
    """Moderation tools for admins."""
    
    def __init__(self, bot):
        self.bot = bot
        self.spam_keywords = ['spam', 'scam', 'free money', 'click here', 'http://bit.ly']
    
    @commands.hybrid_command(name="purge", description="Delete last N messages (Admin only)")
    @commands.has_permissions(manage_messages=True)
    async def purge_command(self, ctx: commands.Context, amount: int):
        """Delete the specified number of messages."""
        if amount < 1 or amount > 100:
            await ctx.reply("❌ Please specify a number between 1 and 100.", ephemeral=True)
            return
        
        await ctx.defer(ephemeral=True)
        
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include command message
        
        await ctx.followup.send(f"✅ Deleted {len(deleted)-1} messages.", ephemeral=True)
        logger.info(f"{ctx.author} purged {len(deleted)-1} messages in {ctx.channel}")
    
    @commands.hybrid_command(name="slowmode", description="Set channel slowmode (Admin only)")
    @commands.has_permissions(manage_channels=True)
    async def slowmode_command(self, ctx: commands.Context, seconds: int):
        """Set slowmode delay in seconds (0 to disable)."""
        if seconds < 0 or seconds > 21600:  # Max 6 hours
            await ctx.reply("❌ Slowmode must be between 0 and 21600 seconds.", ephemeral=True)
            return
        
        await ctx.channel.edit(slowmode_delay=seconds)
        
        if seconds == 0:
            await ctx.reply("✅ Slowmode disabled.", ephemeral=True)
        else:
            await ctx.reply(f"✅ Slowmode set to {seconds} seconds.", ephemeral=True)
        
        logger.info(f"{ctx.author} set slowmode to {seconds}s in {ctx.channel}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Auto-delete spam messages."""
        if message.author.bot:
            return
        
        # Check for spam keywords
        content_lower = message.content.lower()
        for keyword in self.spam_keywords:
            if keyword in content_lower:
                try:
                    await message.delete()
                    logger.warning(f"Deleted spam message from {message.author}: {message.content[:50]}")
                    
                    # Notify user
                    await message.channel.send(
                        f"{message.author.mention}, your message was removed for containing spam keywords.",
                        delete_after=10
                    )
                    return
                except discord.Forbidden:
                    logger.error(f"Missing permissions to delete message from {message.author}")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
