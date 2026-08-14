import asyncio
import json
import logging

from discord.ext import commands

from promotion import PromotionConfig, PromotionService

logger = logging.getLogger("thronos_bot.promotion_worker")


class CommunityPromotion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.task = None
        try:
            self.service = PromotionService(bot, PromotionConfig.from_env())
        except (ValueError, TypeError) as exc:
            self.service = None
            logger.error("Promotion configuration rejected: %s", exc)
        if self.service and self.service.config.enabled:
            self.task = asyncio.create_task(self.worker())

    async def worker(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await self.service.run_once()
            except Exception:
                # Keep the server worker alive without logging request bodies or secrets.
                logger.exception("Unexpected promotion worker error")
            await asyncio.sleep(self.service.config.interval_seconds)

    def cog_unload(self):
        if self.task:
            self.task.cancel()

    @commands.hybrid_command(name="promotion_status", description="Safe promotion worker diagnostics")
    @commands.has_permissions(administrator=True)
    async def status(self, ctx):
        data = self.service.diagnostics() if self.service else {"enabled": False, "last_safe_error_code": "INVALID_CONFIG"}
        await ctx.reply(f"```json\n{json.dumps(data, indent=2)}\n```", ephemeral=True)


async def setup(bot):
    await bot.add_cog(CommunityPromotion(bot))
