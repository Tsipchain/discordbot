import discord
from discord.ext import commands, tasks
import aiohttp
import logging

logger = logging.getLogger('thronos_bot.ticker')

class TickerStatus(commands.Cog):
    """Display THR price in bot's status."""
    
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://thrchain.up.railway.app/api"
        self.update_status.start()
    
    def cog_unload(self):
        self.update_status.cancel()
    
    @tasks.loop(minutes=2)
    async def update_status(self):
        """Update bot status with THR price and TX count."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get price
                async with session.get(f"{self.base_url}/token/prices", timeout=10) as resp:
                    if resp.status == 200:
                        prices = await resp.json()
                        thr_price = prices.get("thr_usd_rate", 0)
                    else:
                        thr_price = 0
                
                # Get TX count
                async with session.get(f"{self.base_url}/network_stats", timeout=10) as resp:
                    if resp.status == 200:
                        stats = await resp.json()
                        tx_count = stats.get("tx_count", 0) if isinstance(stats, dict) else 0
                    else:
                        tx_count = 0
            
            # Update presence
            if isinstance(thr_price, (int, float)) and thr_price > 0:
                status_text = f"${thr_price:.6f} THR | {tx_count:,} TXs"
            else:
                status_text = f"{tx_count:,} transactions"
            
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=status_text
                )
            )
            logger.debug(f"Updated status: {status_text}")
            
        except Exception as e:
            logger.error(f"Error updating ticker status: {e}")
    
    @update_status.before_loop
    async def before_update_status(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(TickerStatus(bot))
