import discord
from discord.ext import commands, tasks
import logging
import database as db

logger = logging.getLogger('thronos_bot.leaderboard')

class Leaderboard(commands.Cog):
    """Track user engagement and display leaderboard."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Track message count for leaderboard."""
        if message.author.bot:
            return
        
        db.update_user_stats(
            user_id=message.author.id,
            username=str(message.author),
            messages=1
        )
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Track reactions given."""
        if user.bot:
            return
        
        db.update_user_stats(
            user_id=user.id,
            username=str(user),
            reactions=1
        )
    
    @commands.hybrid_command(name="leaderboard", description="Show top community members")
    async def leaderboard_command(self, ctx: commands.Context):
        """Display the server leaderboard."""
        top_users = db.get_leaderboard(10)
        
        if not top_users:
            await ctx.reply("No leaderboard data yet. Start chatting to earn XP!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 Community Leaderboard",
            description="Top contributors based on engagement",
            color=0xf1c40f
        )
        
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        
        leaderboard_text = ""
        for i, user in enumerate(top_users):
            leaderboard_text += f"{medals[i]} **{user['username']}**\n"
            leaderboard_text += f"   XP: `{user['xp']}` | 💬 {user['message_count']} | 👍 {user['reaction_count']}\n"
        
        embed.description = leaderboard_text
        embed.set_footer(text="XP: Messages=10, Reactions=5, Referrals=50")
        
        await ctx.reply(embed=embed)
    
    @commands.hybrid_command(name="rank", description="Show your rank and stats")
    async def rank_command(self, ctx: commands.Context):
        """Display user's current rank and stats."""
        rank, user_stats = db.get_user_rank(ctx.author.id)
        
        if not user_stats:
            await ctx.reply("You haven't earned any XP yet. Start chatting!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"📊 Your Stats",
            color=0x3498db
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="🏆 Rank", value=f"#{rank}", inline=True)
        embed.add_field(name="⭐ XP", value=f"{user_stats['xp']}", inline=True)
        embed.add_field(name="💬 Messages", value=f"{user_stats['message_count']}", inline=True)
        embed.add_field(name="👍 Reactions", value=f"{user_stats['reaction_count']}", inline=True)
        embed.add_field(name="👥 Referrals", value=f"{user_stats['referral_count']}", inline=True)
        
        await ctx.reply(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
