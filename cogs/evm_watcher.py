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
        raw_url = os.getenv("THRONOS_API_URL", "https://api.thronoschain.org/api").rstrip("/")
        self.base_url = raw_url if raw_url.endswith("/api") else f"{raw_url}/api"
        self.seen_contracts = set()
        self.first_run = True
        self.watch_evm.start()
    
    def cog_unload(self):
        self.watch_evm.cancel()
        
    @tasks.loop(minutes=15)
    async def watch_evm(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/evm/latest_contracts", timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        contracts = data.get("contracts", [])
                        
                        if self.first_run:
                            # On first run, populate the seen set without announcing
                            for contract in contracts:
                                addr = contract.get("address", "")
                                if addr:
                                    self.seen_contracts.add(addr)
                            self.first_run = False
                            logger.info(f"EVM Watcher initialized with {len(self.seen_contracts)} known contracts")
                            return
                        
                        # Only announce genuinely new contracts
                        new_contracts = []
                        for contract in contracts:
                            addr = contract.get("address", "")
                            if addr and addr not in self.seen_contracts:
                                self.seen_contracts.add(addr)
                                new_contracts.append(contract)
                        
                        if new_contracts:
                            for guild in self.bot.guilds:
                                channel = discord.utils.get(guild.text_channels, name="smart-contracts")
                                if channel:
                                    for contract in new_contracts:
                                        embed = discord.Embed(
                                            title="📜 New EVM Contract Deployed!",
                                            description=f"Address: `{contract.get('address', 'Unknown')}`",
                                            color=0xe67e22
                                        )
                                        embed.add_field(name="Deployer", value=f"`{contract.get('deployer', 'Unknown')}`")
                                        if contract.get("created_at"):
                                            embed.add_field(name="Deployed", value=contract["created_at"], inline=True)
                                        if contract.get("balance") is not None:
                                            embed.add_field(name="Balance", value=f"`{contract['balance']}` THR", inline=True)
                                        await channel.send(embed=embed)
                            logger.info(f"Announced {len(new_contracts)} new contract(s)")
        except Exception as e:
            logger.error(f"EVM Watcher error: {e}")
            
    @watch_evm.before_loop
    async def before_watch(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(EVMWatcher(bot))
