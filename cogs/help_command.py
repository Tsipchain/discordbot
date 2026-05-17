import discord
from discord.ext import commands
from utils.locales import get_text
import logging

logger = logging.getLogger('thronos_bot.help')

class CustomHelp(commands.Cog):
    """Custom multilingual help command."""
    
    def __init__(self, bot):
        self.bot = bot
        # Remove default help
        self.bot.remove_command('help')
    
    def get_user_lang(self, user):
        """Get user's preferred language from roles."""
        lang_roles = {
            "English": "EN",
            "Greek": "GR",
            "Spanish": "ES",
            "Russian": "RU",
            "Japanese": "JA"
        }
        
        for role in user.roles:
            if role.name in lang_roles:
                return lang_roles[role.name]
        
        return "EN"  # Default to English
    
    @commands.hybrid_command(name="help", description="Show bot commands and usage")
    async def help_command(self, ctx: commands.Context, command: str = None):
        """Display help information in user's preferred language."""
        lang = self.get_user_lang(ctx.author)
        
        help_data = {
            "EN": {
                "title": "🤖 Thronos Bot Commands",
                "desc": "Here are all available commands:",
                "cat_network": "📊 Network & Stats",
                "cat_defi": "💰 DeFi & Tokens",
                "cat_ai": "🤖 AI Network",
                "cat_community": "🏆 Community",
                "cat_governance": "🏛️ Governance",
                "cat_admin": "🛡️ Admin",
                "footer": "For support, contact an administrator"
            },
            "GR": {
                "title": "🤖 Εντολές Thronos Bot",
                "desc": "Εδώ είναι όλες οι διαθέσιμες εντολές:",
                "cat_network": "📊 Δίκτυο & Στατιστικά",
                "cat_defi": "💰 DeFi & Tokens",
                "cat_ai": "🤖 AI Δίκτυο",
                "cat_community": "🏆 Κοινότητα",
                "cat_governance": "🏛️ Διακυβέρνηση",
                "cat_admin": "🛡️ Διαχείριση",
                "footer": "Για υποστήριξη, επικοινωνήστε με έναν διαχειριστή"
            },
            "ES": {
                "title": "🤖 Comandos de Thronos Bot",
                "desc": "Aquí están todos los comandos disponibles:",
                "cat_network": "📊 Red y Estadísticas",
                "cat_defi": "💰 DeFi y Tokens",
                "cat_ai": "🤖 Red de IA",
                "cat_community": "🏆 Comunidad",
                "cat_governance": "🏛️ Gobernanza",
                "cat_admin": "🛡️ Administración",
                "footer": "Para soporte, contacte a un administrador"
            },
            "RU": {
                "title": "🤖 Команды Thronos Bot",
                "desc": "Вот все доступные команды:",
                "cat_network": "📊 Сеть и Статистика",
                "cat_defi": "💰 DeFi и Токены",
                "cat_ai": "🤖 Сеть ИИ",
                "cat_community": "🏆 Сообщество",
                "cat_governance": "🏛️ Управление",
                "cat_admin": "🛡️ Администрирование",
                "footer": "Для поддержки свяжитесь с администратором"
            },
            "JA": {
                "title": "🤖 Thronos Bot コマンド",
                "desc": "利用可能なコマンド一覧:",
                "cat_network": "📊 ネットワーク & 統計",
                "cat_defi": "💰 DeFi & トークン",
                "cat_ai": "🤖 AIネットワーク",
                "cat_community": "🏆 コミュニティ",
                "cat_governance": "🏛️ ガバナンス",
                "cat_admin": "🛡️ 管理者",
                "footer": "サポートについては管理者にお問い合わせください"
            }
        }
        
        text = help_data.get(lang, help_data["EN"])
        
        embed = discord.Embed(
            title=text["title"],
            description=text["desc"],
            color=0x3498db
        )
        
        embed.add_field(name=text["cat_network"], value=(
            "**!stats** — Live network statistics\n"
            "**!price** — THR token price\n"
        ), inline=False)
        
        embed.add_field(name=text["cat_defi"], value=(
            "**!tokens** — All tokens on the network\n"
            "**!token <symbol>** — Token details\n"
            "**!pools** — Liquidity pools & TVL\n"
        ), inline=False)
        
        embed.add_field(name=text["cat_ai"], value=(
            "**!ask <message>** — Query the Thronos AI\n"
            "**!bind <address>** — Bind wallet for AI credits\n"
        ), inline=False)
        
        embed.add_field(name=text["cat_community"], value=(
            "**!leaderboard** — Top members by XP\n"
            "**!rank** — Your stats & rank\n"
            "**!help** — This help menu\n"
        ), inline=False)
        
        embed.add_field(name=text["cat_governance"], value=(
            "**!propose \"Title\" desc** — Create a vote (Admin)\n"
            "**!proposals** — List all proposals\n"
        ), inline=False)
        
        embed.add_field(name=text["cat_admin"], value=(
            "**!setup_server** — Auto-configure channels (Admin)\n"
            "**!announce <msg>** — Broadcast message (Admin)\n"
            "**!purge <N>** — Delete N messages (Admin)\n"
            "**!sync_now** — Force content sync (Admin)\n"
        ), inline=False)
        
        embed.set_footer(text=text["footer"])
        
        await ctx.reply(embed=embed, ephemeral=True)
        logger.info(f"Help command used by {ctx.author} in language {lang}")

async def setup(bot):
    await bot.add_cog(CustomHelp(bot))
