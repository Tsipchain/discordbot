import discord
from discord.ext import commands, tasks
from cogs.server_setup import ServerSetup
import logging

logger = logging.getLogger('thronos_bot.auto_sync')

class AutoSync(commands.Cog):
    """Automatically syncs content from website every 24 hours."""
    
    def __init__(self, bot):
        self.bot = bot
        self.sync_content.start()
    
    def cog_unload(self):
        self.sync_content.cancel()
    
    @tasks.loop(hours=24)
    async def sync_content(self):
        """Background task to refresh Roadmap/Whitepaper content."""
        try:
            logger.info("Starting automated content sync...")
            
            # Get the server_setup cog to reuse its methods
            server_setup_cog = self.bot.get_cog('ServerSetup')
            
            if not server_setup_cog:
                logger.error("ServerSetup cog not found, cannot sync content")
                return
            
            for guild in self.bot.guilds:
                logger.info(f"Syncing content for guild: {guild.name}")
                
                # 1. Update Roadmap
                roadmap_channel = discord.utils.get(guild.text_channels, name="roadmap")
                if roadmap_channel:
                    try:
                        roadmap_embed = await server_setup_cog.get_roadmap_embed()
                        
                        # Find and update bot's message
                        async for message in roadmap_channel.history(limit=10):
                            if message.author == self.bot.user and message.embeds:
                                await message.edit(embed=roadmap_embed)
                                logger.info(f"Updated roadmap in {guild.name}")
                                break
                    except Exception as e:
                        logger.error(f"Error syncing roadmap: {e}")
                
                # 2. Update Whitepaper
                whitepaper_channel = discord.utils.get(guild.text_channels, name="whitepaper")
                if whitepaper_channel:
                    try:
                        whitepaper_embed = await server_setup_cog.get_whitepaper_embed()
                        
                        # Find and update bot's message
                        async for message in whitepaper_channel.history(limit=10):
                            if message.author == self.bot.user and message.embeds:
                                await message.edit(embed=whitepaper_embed)
                                logger.info(f"Updated whitepaper in {guild.name}")
                                break
                    except Exception as e:
                        logger.error(f"Error syncing whitepaper: {e}")
            
            logger.info("Automated content sync completed")
        
        except Exception as e:
            logger.error(f"Error in sync_content task: {e}")
    
    @sync_content.before_loop
    async def before_sync_content(self):
        await self.bot.wait_until_ready()
    
    @commands.hybrid_command(name="sync_now", description="Manually trigger content sync (Admin only)")
    @commands.has_permissions(administrator=True)
    async def sync_now_command(self, ctx: commands.Context):
        """Manual command to trigger immediate sync."""
        await ctx.defer()
        
        await self.sync_content()
        
        await ctx.reply("✅ Content sync completed!")
        logger.info(f"Manual sync triggered by {ctx.author}")

async def setup(bot):
    await bot.add_cog(AutoSync(bot))
