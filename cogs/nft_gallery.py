import discord
from discord.ext import commands, tasks
import aiohttp
import logging
import os

logger = logging.getLogger('thronos_bot.nft_gallery')

class NFTGallery(commands.Cog):
    """Display tokens/NFTs from the Thronos network."""
    
    def __init__(self, bot):
        self.bot = bot
        self.base_url = os.getenv("THRONOS_API_URL", "https://api.thronoschain.org/api")
    
    @commands.hybrid_command(name="tokens", description="Show all tokens on the network")
    async def tokens_command(self, ctx: commands.Context):
        """Display all tokens from the network."""
        await ctx.defer()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/tokens/list", timeout=10) as resp:
                    if resp.status != 200:
                        await ctx.reply("❌ Failed to fetch tokens.", ephemeral=True)
                        return
                    tokens = await resp.json()
                
                async with session.get(f"{self.base_url}/tokens/stats", timeout=10) as resp:
                    stats = await resp.json() if resp.status == 200 else []
            
            if not isinstance(tokens, list):
                await ctx.reply("❌ Invalid token data.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🪙 Thronos Token Gallery",
                description=f"Total tokens: **{len(tokens)}**",
                color=0x9b59b6
            )
            
            # Create stats lookup
            stats_dict = {}
            if isinstance(stats, list):
                for s in stats:
                    if isinstance(s, dict):
                        stats_dict[s.get('symbol', '')] = s
            
            for token in tokens[:12]:
                if not isinstance(token, dict):
                    continue
                    
                symbol = token.get('symbol', 'Unknown')
                name = token.get('name', 'Unknown')
                
                # Get stats for this token
                token_stats = stats_dict.get(symbol, {})
                supply = token_stats.get('total_supply', 'N/A')
                holders = token_stats.get('holders_count', 'N/A')
                
                embed.add_field(
                    name=f"🪙 {symbol}",
                    value=f"**{name}**\nSupply: `{supply}`\nHolders: `{holders}`",
                    inline=True
                )
            
            if len(tokens) > 12:
                embed.set_footer(text=f"Showing 12 of {len(tokens)} tokens")
            
            await ctx.reply(embed=embed)
            logger.info(f"Tokens displayed for {ctx.author}")
            
        except Exception as e:
            logger.error(f"Error in tokens command: {e}")
            await ctx.reply(f"❌ Error: {str(e)}", ephemeral=True)
    
    @commands.hybrid_command(name="token", description="Show details for a specific token")
    async def token_detail_command(self, ctx: commands.Context, symbol: str):
        """Display detailed info for a specific token."""
        await ctx.defer()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/tokens/list", timeout=10) as resp:
                    if resp.status != 200:
                        await ctx.reply("❌ Failed to fetch tokens.", ephemeral=True)
                        return
                    tokens = await resp.json()
                
                async with session.get(f"{self.base_url}/tokens/stats", timeout=10) as resp:
                    stats = await resp.json() if resp.status == 200 else []
            
            # Find token
            token = None
            for t in tokens:
                if isinstance(t, dict) and t.get('symbol', '').upper() == symbol.upper():
                    token = t
                    break
            
            if not token:
                await ctx.reply(f"❌ Token `{symbol}` not found.", ephemeral=True)
                return
            
            # Find stats
            token_stats = {}
            if isinstance(stats, list):
                for s in stats:
                    if isinstance(s, dict) and s.get('symbol', '').upper() == symbol.upper():
                        token_stats = s
                        break
            
            embed = discord.Embed(
                title=f"🪙 {token.get('symbol', 'Unknown')}",
                description=token.get('name', 'Unknown Token'),
                color=0x9b59b6
            )
            
            embed.add_field(name="Total Supply", value=f"`{token_stats.get('total_supply', 'N/A')}`", inline=True)
            embed.add_field(name="Holders", value=f"`{token_stats.get('holders_count', 'N/A')}`", inline=True)
            embed.add_field(name="Decimals", value=f"`{token.get('decimals', 'N/A')}`", inline=True)
            
            if token.get('logo'):
                embed.set_thumbnail(url=token['logo'])
            
            await ctx.reply(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in token detail command: {e}")
            await ctx.reply(f"❌ Error: {str(e)}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(NFTGallery(bot))
