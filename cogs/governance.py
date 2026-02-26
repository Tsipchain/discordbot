import discord
from discord.ext import commands
import logging
import database as db

logger = logging.getLogger('thronos_bot.governance')

class Governance(commands.Cog):
    """Interactive DAO voting with persistent storage."""
    
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(PersistentVotingView(self))
    
    @commands.hybrid_command(name="propose", description="Create a new governance proposal (Admin only)")
    @commands.has_permissions(administrator=True)
    async def propose_command(self, ctx: commands.Context, title: str, *, description: str):
        """Create a new proposal for voting."""
        governance_channel = discord.utils.get(ctx.guild.text_channels, name="governance")
        
        if not governance_channel:
            await ctx.reply("❌ Governance channel not found.", ephemeral=True)
            return
        
        # Create embed first with placeholder ID
        embed = discord.Embed(
            title=f"🏛️ Proposal: {title}",
            description=description,
            color=0x9b59b6
        )
        embed.add_field(name="✅ For", value="0 votes", inline=True)
        embed.add_field(name="❌ Against", value="0 votes", inline=True)
        embed.set_footer(text=f"Proposed by {ctx.author.display_name}")
        
        # Create view with placeholder
        view = PersistentVotingView(self, proposal_id=0)
        message = await governance_channel.send(embed=embed, view=view)
        
        # Store in database
        proposal_id = db.create_proposal(
            title=title,
            description=description,
            author_id=ctx.author.id,
            author_name=ctx.author.display_name,
            message_id=message.id,
            channel_id=governance_channel.id
        )
        
        # Update embed with real ID
        embed.title = f"🏛️ Proposal #{proposal_id}: {title}"
        view = PersistentVotingView(self, proposal_id=proposal_id)
        await message.edit(embed=embed, view=view)
        
        await ctx.reply(f"✅ Proposal #{proposal_id} created!", ephemeral=True)
        logger.info(f"{ctx.author} created proposal #{proposal_id}: {title}")
    
    @commands.hybrid_command(name="proposals", description="List all proposals")
    async def proposals_command(self, ctx: commands.Context):
        """List all governance proposals."""
        proposals = db.get_all_proposals()
        
        if not proposals:
            await ctx.reply("No proposals found.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏛️ All Proposals",
            color=0x9b59b6
        )
        
        for p in proposals[:10]:
            status = "🟢" if p['votes_yes'] > p['votes_no'] else ("🔴" if p['votes_no'] > p['votes_yes'] else "⚪")
            embed.add_field(
                name=f"#{p['id']}: {p['title']}",
                value=f"{status} ✅{p['votes_yes']} | ❌{p['votes_no']}",
                inline=True
            )
        
        await ctx.reply(embed=embed, ephemeral=True)
    
    async def update_proposal_embed(self, proposal_id):
        """Update the proposal embed with current vote counts."""
        proposal = db.get_proposal(proposal_id)
        if not proposal:
            return
        
        try:
            channel = self.bot.get_channel(proposal["channel_id"])
            message = await channel.fetch_message(proposal["message_id"])
            
            embed = message.embeds[0]
            embed.set_field_at(0, name="✅ For", value=f"{proposal['votes_yes']} votes", inline=True)
            embed.set_field_at(1, name="❌ Against", value=f"{proposal['votes_no']} votes", inline=True)
            
            await message.edit(embed=embed)
        except Exception as e:
            logger.error(f"Error updating proposal embed: {e}")


class PersistentVotingView(discord.ui.View):
    """Persistent voting buttons that survive bot restarts."""
    
    def __init__(self, cog, proposal_id=0):
        super().__init__(timeout=None)
        self.cog = cog
        self.proposal_id = proposal_id
    
    @discord.ui.button(label="Vote For", style=discord.ButtonStyle.green, emoji="✅", custom_id="vote_yes")
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.register_vote(interaction, "yes")
    
    @discord.ui.button(label="Vote Against", style=discord.ButtonStyle.red, emoji="❌", custom_id="vote_no")
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.register_vote(interaction, "no")
    
    async def register_vote(self, interaction: discord.Interaction, vote_type: str):
        """Register a user's vote in the database."""
        # Get proposal_id from message embed title
        if self.proposal_id == 0:
            try:
                title = interaction.message.embeds[0].title
                self.proposal_id = int(title.split("#")[1].split(":")[0])
            except:
                await interaction.response.send_message("❌ Could not identify proposal.", ephemeral=True)
                return
        
        proposal = db.get_proposal(self.proposal_id)
        if not proposal:
            await interaction.response.send_message("❌ Proposal not found.", ephemeral=True)
            return
        
        user_id = interaction.user.id
        
        if db.has_voted(self.proposal_id, user_id):
            await interaction.response.send_message("❌ You have already voted.", ephemeral=True)
            return
        
        # Register vote
        if db.add_vote(self.proposal_id, user_id, vote_type):
            votes_yes = proposal['votes_yes'] + (1 if vote_type == "yes" else 0)
            votes_no = proposal['votes_no'] + (1 if vote_type == "no" else 0)
            db.update_proposal_votes(self.proposal_id, votes_yes, votes_no)
            
            await self.cog.update_proposal_embed(self.proposal_id)
            await interaction.response.send_message("✅ Vote recorded!", ephemeral=True)
            logger.info(f"{interaction.user} voted {vote_type} on proposal #{self.proposal_id}")
        else:
            await interaction.response.send_message("❌ Vote failed.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Governance(bot))
