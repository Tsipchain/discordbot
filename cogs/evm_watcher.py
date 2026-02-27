import discord
from discord.ext import commands, tasks
import aiohttp
import logging
import os

logger = logging.getLogger('thronos_bot.evm')

class EVMWatcher(commands.Cog):
    """Monitors Thronos EVM subnet for new contract deployments."""
    
    def __init__(self, bot):
        self.bot = bot
        self.base_url = os.getenv("THRONOS_API_URL", "https://api.thronoschain.org/api")
        self.watch_evm.start()
    
    def cog_unload(self):
        self.watch_evm.cancel()
        
    @tasks.loop(minutes=3)
    async def watch_evm(self):
        try:
            # Poll the Thronos Network for recent smart contracts
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/evm/latest_contracts", timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        contracts = data.get("contracts", [])
                        
                        if contracts:
                            for guild in self.bot.guilds:
                                channel = discord.utils.get(guild.text_channels, name="smart-contracts")
                                if channel:
                                    for contract in contracts:
                                        embed = discord.Embed(
                                            title="📜 New EVM Contract Deployed!",
                                            description=f"Address: `{contract.get('address', 'Unknown')}`",
                                            color=0xe67e22
                                        )
                                        embed.add_field(name="Deployer", value=f"`{contract.get('deployer', 'Unknown')}`")
                                        await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"EVM Watcher error: {e}")
            
    @watch_evm.before_loop
    async def before_watch(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(EVMWatcher(bot))
