import discord
from discord.ext import commands, tasks
import aiohttp
import logging

logger = logging.getLogger('thronos_bot.network_stats')

class NetworkStats(commands.Cog):
    """Fetches and displays real-time network statistics from the Thronos API."""
    
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://thrchain.up.railway.app/api"
        self.update_stats.start()
    
    def cog_unload(self):
        self.update_stats.cancel()
    
    async def fetch_api(self, endpoint):
        """Helper to fetch data from API endpoints."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}{endpoint}", timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"API {endpoint} returned status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching {endpoint}: {e}")
            return None
    
    @tasks.loop(minutes=5)
    async def update_stats(self):
        """Background task to update network stats every 5 minutes."""
        try:
            # Find the network-stats channel
            for guild in self.bot.guilds:
                channel = discord.utils.get(guild.text_channels, name="network-stats")
                if channel:
                    embed = await self.generate_stats_embed()
                    if embed:
                        # Update or create message
                        last_msg = None
                        async for message in channel.history(limit=5):
                            if message.author == self.bot.user and message.embeds:
                                last_msg = message
                                break
                        
                        if last_msg:
                            await last_msg.edit(embed=embed)
                        else:
                            await channel.send(embed=embed)
                        
                        logger.info(f"Updated network stats in {guild.name}")
        except Exception as e:
            logger.error(f"Error in update_stats task: {e}")
    
    @update_stats.before_loop
    async def before_update_stats(self):
        await self.bot.wait_until_ready()
    
    async def generate_stats_embed(self):
        """Generate the stats embed from API data."""
        # Fetch data from all endpoints
        network_data = await self.fetch_api("/network_stats")
        prices_data = await self.fetch_api("/token/prices")
        health_data = await self.fetch_api("/health")
        dashboard_data = await self.fetch_api("/dashboard")
        tokens_data = await self.fetch_api("/tokens/stats")
        
        # Validate that we got dict responses (not strings/errors)
        if not isinstance(network_data, dict):
            logger.error(f"network_data is not a dict: {type(network_data)}")
            return None
        
        embed = discord.Embed(
            title="📊 Live Network Statistics",
            description="Real-time data from Thronos Network",
            color=0x00ff00 if (isinstance(health_data, dict) and health_data.get("ok")) else 0xff0000
        )
        
        # Network Stats
        tx_count = network_data.get("tx_count", "N/A")
        block_count = network_data.get("block_count", "N/A")
        total_supply = network_data.get("total_supply", "N/A")
        burned = network_data.get("burned", "N/A")
        
        embed.add_field(
            name="🔢 Transaction Count", 
            value=f"`{tx_count:,}` transactions" if isinstance(tx_count, int) else tx_count, 
            inline=True
        )
        embed.add_field(
            name="📦 Block Height", 
            value=f"`{block_count:,}` blocks" if isinstance(block_count, int) else block_count, 
            inline=True
        )
        
        # Token Price
        if isinstance(prices_data, dict):
            thr_price = prices_data.get("thr_usd_rate", prices_data.get("prices", {}).get("THR", "N/A"))
            embed.add_field(
                name="💰 THR Price", 
                value=f"`${thr_price:.6f}` USD" if isinstance(thr_price, (int, float)) else "N/A", 
                inline=True
            )
        
        # Active Wallets (from token stats)
        if isinstance(tokens_data, list):
            # Find THR token holders
            thr_holders = 0
            for token_stat in tokens_data:
                if isinstance(token_stat, dict):
                    if token_stat.get("symbol") == "THR" or token_stat.get("name") == "Thronos":
                        thr_holders = token_stat.get("holders_count", 0)
                        break
            
            if thr_holders > 0:
                embed.add_field(
                    name="👥 Active Wallets", 
                    value=f"`{thr_holders:,}` holders", 
                    inline=True
                )
        
        # Dashboard Data
        if isinstance(dashboard_data, dict):
            tps = dashboard_data.get("tps", "N/A")
            token_count = dashboard_data.get("token_count", "N/A")
            pool_count = dashboard_data.get("pool_count", "N/A")
            
            embed.add_field(
                name="⚡ TPS", 
                value=f"`{tps:.4f}`" if isinstance(tps, (int, float)) else "N/A", 
                inline=True
            )
            embed.add_field(
                name="🪙 Total Tokens", 
                value=f"`{token_count}`" if isinstance(token_count, int) else "N/A", 
                inline=True
            )
            embed.add_field(
                name="💧 Liquidity Pools", 
                value=f"`{pool_count}`" if isinstance(pool_count, int) else "N/A", 
                inline=True
            )
        
        # Supply Info
        embed.add_field(
            name="📊 Total Supply", 
            value=f"`{total_supply:,}` THR" if isinstance(total_supply, (int, float)) else "N/A", 
            inline=True
        )
        embed.add_field(
            name="🔥 Burned", 
            value=f"`{burned:,}` THR" if isinstance(burned, (int, float)) else "N/A", 
            inline=True
        )
        
        # Health Status
        if isinstance(health_data, dict):
            status_emoji = "🟢" if health_data.get("ok") else "🔴"
            version = health_data.get("version", "N/A")
            embed.add_field(
                name="🏥 Network Health", 
                value=f"{status_emoji} `{version}`", 
                inline=True
            )
        
        embed.set_footer(text="Updates every 5 minutes")
        embed.timestamp = discord.utils.utcnow()
        
        return embed
    
    @commands.hybrid_command(name="stats", description="Show current network statistics")
    async def stats_command(self, ctx: commands.Context):
        """Manual command to fetch latest stats."""
        logger.info(f"Stats command triggered by {ctx.author}")
        
        try:
            await ctx.defer()
            logger.info("Deferred successfully, fetching stats...")
            
            embed = await self.generate_stats_embed()
            
            if embed:
                await ctx.reply(embed=embed)
                logger.info("Stats embed sent successfully")
            else:
                await ctx.reply("❌ Failed to fetch network statistics. API might be down.")
                logger.warning("Stats embed generation returned None")
                
        except Exception as e:
            logger.error(f"Error in stats_command: {e}", exc_info=True)
            try:
                await ctx.reply(f"❌ Error fetching stats: {str(e)}")
            except:
                pass

async def setup(bot):
    await bot.add_cog(NetworkStats(bot))
