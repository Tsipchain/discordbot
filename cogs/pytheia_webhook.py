import discord
from discord.ext import commands
import logging
from aiohttp import web
import asyncio
import os

logger = logging.getLogger('thronos_bot.pytheia')

class PytheiaWebhook(commands.Cog):
    """Listens for Pytheia Autonomous Agent trades and alerts Discord."""
    
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.app.router.add_post('/pytheia/alert', self.handle_alert)
        self.runner = None
        self.site = None
        
        # Start the webhook server when cog loads
        self.bot.loop.create_task(self.start_server())
        
    async def start_server(self):
        await self.bot.wait_until_ready()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        # Bind to PORT from environment (fallback to 5005) for external Vercel/Railway hosting
        port = int(os.getenv("PORT", 5005))
        self.site = web.TCPSite(self.runner, '0.0.0.0', port)
        await self.site.start()
        logger.info(f"Pytheia Webhook listening on 0.0.0.0:{port}/pytheia/alert")

    def cog_unload(self):
        if self.runner:
            asyncio.create_task(self.runner.cleanup())
            
    async def handle_alert(self, request):
        try:
            data = await request.json()
            
            # Route to all guilds #autonomous-trading channel
            for guild in self.bot.guilds:
                channel = discord.utils.get(guild.text_channels, name="autonomous-trading")
                if not channel:
                    category = discord.utils.get(guild.categories, name="🛠️ Ecosystem")
                    if category:
                        channel = await guild.create_text_channel("autonomous-trading", category=category)
                
                if channel:
                    embed = discord.Embed(
                        title="🤖 Pytheia Autonomous Trade executed",
                        color=0xf1c40f
                    )
                    
                    if "trade_type" in data:
                        embed.add_field(name="Action", value=data["trade_type"], inline=True)
                    if "amount" in data and "token" in data:
                        embed.add_field(name="Amount", value=f"{data['amount']} {data['token']}", inline=True)
                    if "profit_estimate" in data:
                        embed.add_field(name="Expected Profit", value=f"{data['profit_estimate']}", inline=True)
                    
                    if "tx_hash" in data:
                        embed.description = f"[View on Explorer](https://explorer.thronoschain.org/tx/{data['tx_hash']})"
                        
                    embed.set_footer(text="Pytheia AI Network Layer")
                    await channel.send(embed=embed)
                    
            return web.json_response({"status": "delivered"})
        except Exception as e:
            logger.error(f"Error handling pytheia webhook: {e}")
            return web.json_response({"error": str(e)}, status=500)

async def setup(bot):
    await bot.add_cog(PytheiaWebhook(bot))
