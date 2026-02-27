import discord
from discord.ext import commands
import aiohttp
import logging
import os
import database as db

logger = logging.getLogger('thronos_bot.ai_chat')

class AIChat(commands.Cog):
    """Interact with the Thronos V3.6 AI Network."""
    
    def __init__(self, bot):
        self.bot = bot
        self.base_url = os.getenv("THRONOS_API_URL", "https://api.thronoschain.org/api")
    
    @commands.hybrid_command(name="bind", description="Bind your Thronos wallet to your Discord account")
    async def bind_wallet(self, ctx: commands.Context, wallet_address: str):
        """Bind your wallet to allow AI credit consumption."""
        if not wallet_address.startswith("0x") and len(wallet_address) != 42:
            # Basic validation
            await ctx.reply("❌ Invalid wallet address format. Usually starts with 0x.", ephemeral=True)
            return

        db.bind_wallet(ctx.author.id, ctx.author.display_name, wallet_address)
        await ctx.reply(f"✅ Successfully bound wallet `{wallet_address}` to your account! You can now use your on-chain AI credits.", ephemeral=True)
        logger.info(f"{ctx.author} bound wallet {wallet_address}")
    
    @commands.hybrid_command(name="ask", description="Ask a question to the Thronos AI Network")
    async def ask_ai(self, ctx: commands.Context, *, message: str):
        """Send a prompt to the Thronos AI (/api/ai/chat)."""
        logger.info(f"AI chat request from {ctx.author}")
        
        try:
            # We defer early because AI generation might take seconds
            await ctx.defer()
            
            # Use Discord User ID as a stable session identifier across requests
            session_id = f"discord_{ctx.author.id}"
            
            # Fetch bound wallet
            wallet = db.get_wallet(ctx.author.id)
            
            payload = {
                "message": message,
                "session_id": session_id,
            }
            if wallet:
                payload["wallet"] = wallet
            
            async with aiohttp.ClientSession() as session:
                endpoint = f"{self.base_url}/ai/chat"
                async with session.post(endpoint, json=payload, timeout=60) as response:
                    if response.status == 200:
                        data = await response.json()
                        reply = data.get("assistant_message") or data.get("response") or "No response from AI."
                        model_id = data.get("model_id", "unknown")
                        
                        embed = discord.Embed(
                            title="🤖 AI Response",
                            description=reply,
                            color=0x4a90e2
                        )
                        embed.set_footer(text=f"Model: {model_id} | Session: {session_id}")
                        await ctx.reply(embed=embed)
                    else:
                        logger.warning(f"AI API returned status {response.status}")
                        await ctx.reply(f"❌ Failed to reach AI provider (Status {response.status}). Keep in mind some features may require a synced wallet.")
                        
        except Exception as e:
            logger.error(f"Error in ask_ai: {e}", exc_info=True)
            await ctx.reply("❌ An error occurred while communicating with the AI service.")

async def setup(bot):
    await bot.add_cog(AIChat(bot))
