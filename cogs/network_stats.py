import discord
from discord.ext import commands, tasks
import aiohttp
import logging
import os

logger = logging.getLogger('thronos_bot.network_stats')

class NetworkStats(commands.Cog):
    """Fetches and displays real-time network statistics from the Thronos API."""
    
    def __init__(self, bot):
        self.bot = bot
        raw_url = os.getenv("THRONOS_API_URL", "https://api.thronoschain.org/api").rstrip("/")
        self.base_url = raw_url if raw_url.endswith("/api") else f"{raw_url}/api"
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
            for guild in self.bot.guilds:
                channel = discord.utils.get(guild.text_channels, name="network-stats")
                if channel:
                    embed = await self.generate_stats_embed()
                    if embed:
                        # Update existing message or create new one
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
        network_data = await self.fetch_api("/network_stats")
        prices_data = await self.fetch_api("/token/prices")
        health_data = await self.fetch_api("/health")
        dashboard_data = await self.fetch_api("/dashboard")
        tokens_data = await self.fetch_api("/tokens/stats")
        
        if not isinstance(network_data, dict):
            logger.error(f"network_data is not a dict: {type(network_data)}")
            return None
        
        embed = discord.Embed(
            title="📊 Live Network Statistics",
            description="Real-time data from Thronos Network",
            color=0x00ff00 if (isinstance(health_data, dict) and health_data.get("ok")) else 0xff0000
        )
        
        # Network Stats (merge dashboard data for fields missing from /network_stats)
        dash = dashboard_data if isinstance(dashboard_data, dict) else {}
        tx_count = network_data.get("tx_count", dash.get("tx_count", None))
        block_count = network_data.get("block_count", dash.get("chain_height", None))
        total_supply = network_data.get("total_supply", dash.get("total_supply", None))
        burned = network_data.get("burned", dash.get("burned", None))
        
        # Only show non-zero transaction count
        if isinstance(tx_count, (int, float)) and tx_count > 0:
            embed.add_field(
                name="🔢 Transaction Count", 
                value=f"`{tx_count:,}` transactions", 
                inline=True
            )
        
        if isinstance(block_count, (int, float)) and block_count > 0:
            embed.add_field(
                name="📦 Block Height", 
                value=f"`{int(block_count):,}` blocks", 
                inline=True
            )
        
        # Token Price
        if isinstance(prices_data, dict):
            thr_price = prices_data.get("thr_usd_rate", prices_data.get("prices", {}).get("THR", None))
            if isinstance(thr_price, (int, float)):
                embed.add_field(
                    name="💰 THR Price", 
                    value=f"`${thr_price:.6f}` USD", 
                    inline=True
                )
        
        # Active Wallets (from token stats) — defensive parsing
        token_list = tokens_data
        if isinstance(tokens_data, dict):
            token_list = tokens_data.get("tokens", [])
        if isinstance(token_list, list):
            thr_holders = 0
            for token_stat in token_list:
                if not isinstance(token_stat, dict):
                    continue
                if token_stat.get("symbol") == "THR" or token_stat.get("name") == "Thronos":
                    thr_holders = token_stat.get("holders_count", 0)
                    break
            
            if thr_holders > 0:
                embed.add_field(
                    name="👥 Active Wallets", 
                    value=f"`{thr_holders:,}` holders", 
                    inline=True
                )
        
        # Dashboard Data — graceful zero handling
        if isinstance(dashboard_data, dict):
            tps = dashboard_data.get("tps", None)
            token_count = dashboard_data.get("token_count", None)
            pool_count = dashboard_data.get("pool_count", None)
            
            if isinstance(tps, (int, float)) and tps > 0:
                embed.add_field(
                    name="⚡ TPS", 
                    value=f"`{tps:.4f}`", 
                    inline=True
                )
            
            if isinstance(token_count, int) and token_count > 0:
                embed.add_field(
                    name="🪙 Total Tokens", 
                    value=f"`{token_count}`", 
                    inline=True
                )
            if isinstance(pool_count, int) and pool_count > 0:
                embed.add_field(
                    name="💧 Liquidity Pools", 
                    value=f"`{pool_count}`", 
                    inline=True
                )
        
        # Supply Info
        if isinstance(total_supply, (int, float)):
            embed.add_field(
                name="📊 Total Supply", 
                value=f"`{total_supply:,.2f}` THR", 
                inline=True
            )
        if isinstance(burned, (int, float)) and burned > 0:
            embed.add_field(
                name="🔥 Burned", 
                value=f"`{burned:,.2f}` THR", 
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
            embed = await self.generate_stats_embed()
            
            if embed:
                await ctx.reply(embed=embed)
            else:
                await ctx.reply("❌ Failed to fetch network statistics. API might be down.")
                
        except Exception as e:
            logger.error(f"Error in stats_command: {e}", exc_info=True)
            try:
                await ctx.reply(f"❌ Error fetching stats: {str(e)}")
            except:
                pass

    @commands.hybrid_command(name="pools", description="Show liquidity pools on Thronos Network")
    async def pools_command(self, ctx: commands.Context):
        """Display all liquidity pools with TVL data."""
        logger.info(f"Pools command triggered by {ctx.author}")
        
        try:
            await ctx.defer()
            pools_data = await self.fetch_api("/pools")
            
            if not isinstance(pools_data, dict):
                await ctx.reply("❌ Failed to fetch pool data.")
                return
            
            pool_list = pools_data.get("pools", [])
            if not isinstance(pool_list, list) or not pool_list:
                await ctx.reply("❌ No liquidity pools found.")
                return
            
            total_tvl = sum(p.get("tvl_usd", 0) for p in pool_list if isinstance(p, dict))
            
            embed = discord.Embed(
                title="💧 Thronos Liquidity Pools",
                description=f"**{len(pool_list)}** pools — Total TVL: **${total_tvl:,.2f}**",
                color=0x3498db
            )
            
            for pool in pool_list:
                if not isinstance(pool, dict):
                    continue
                
                token_a = pool.get("token_a", "?")
                token_b = pool.get("token_b", "?")
                tvl_usd = pool.get("tvl_usd", 0)
                reserve_a = pool.get("reserve_a", 0)
                reserve_b = pool.get("reserve_b", 0)
                price = pool.get("price_a_to_b", 0)
                
                value_lines = [
                    f"TVL: `${tvl_usd:,.2f}`",
                    f"{token_a}: `{reserve_a:,.2f}`",
                    f"{token_b}: `{reserve_b:,.2f}`",
                ]
                
                if pool.get("fee_bps"):
                    value_lines.append(f"Fee: `{pool['fee_bps'] / 100:.1f}%`")
                
                embed.add_field(
                    name=f"🔄 {token_a}/{token_b}",
                    value="\n".join(value_lines),
                    inline=True
                )
            
            embed.set_footer(text="Data from Thronos API")
            embed.timestamp = discord.utils.utcnow()
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in pools_command: {e}", exc_info=True)
            try:
                await ctx.reply(f"❌ Error fetching pools: {str(e)}")
            except:
                pass

    @commands.hybrid_command(name="price", description="Show THR token price")
    async def price_command(self, ctx: commands.Context):
        """Quick THR price check."""
        try:
            await ctx.defer()
            prices_data = await self.fetch_api("/token/prices")
            
            if not isinstance(prices_data, dict):
                await ctx.reply("❌ Failed to fetch price data.")
                return
            
            thr_price = prices_data.get("thr_usd_rate", 0)
            wbtc_price = prices_data.get("prices", {}).get("WBTC", 0)
            updated = prices_data.get("last_updated", "N/A")
            
            embed = discord.Embed(
                title="💰 Thronos Price",
                color=0x2ecc71
            )
            
            if isinstance(thr_price, (int, float)):
                embed.add_field(name="THR/USD", value=f"`${thr_price:.6f}`", inline=True)
            if isinstance(wbtc_price, (int, float)) and wbtc_price > 0:
                embed.add_field(name="WBTC/USD", value=f"`${wbtc_price:,.2f}`", inline=True)
                if isinstance(thr_price, (int, float)) and thr_price > 0:
                    thr_btc = thr_price / wbtc_price
                    embed.add_field(name="THR/BTC", value=f"`{thr_btc:.10f}`", inline=True)
            
            embed.set_footer(text=f"Updated: {updated}")
            embed.timestamp = discord.utils.utcnow()
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in price_command: {e}", exc_info=True)
            try:
                await ctx.reply(f"❌ Error fetching price: {str(e)}")
            except:
                pass

async def setup(bot):
    await bot.add_cog(NetworkStats(bot))
