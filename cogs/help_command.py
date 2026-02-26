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
            "Greek": "EL",
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
        
        # Help text in multiple languages
        help_data = {
            "EN": {
                "title": "🤖 Thronos Bot Commands",
                "description": "Here are all available commands:",
                "setup": "**!setup_server** - Auto-configure server channels and content (Admin only)",
                "stats": "**!stats** - Show real-time network statistics",
                "help": "**!help [command]** - Show this help message",
                "lang": "**!language** - Select your preferred language",
                "verify": "Click the Verify button to access channels",
                "footer": "For support, contact an administrator"
            },
            "EL": {
                "title": "🤖 Εντολές Thronos Bot",
                "description": "Εδώ είναι όλες οι διαθέσιμες εντολές:",
                "setup": "**!setup_server** - Αυτόματη διαμόρφωση καναλιών διακομιστή (Μόνο Admin)",
                "stats": "**!stats** - Εμφάνιση στατιστικών δικτύου σε πραγματικό χρόνο",
                "help": "**!help [εντολή]** - Εμφάνιση αυτού του μηνύματος βοηθείας",
                "lang": "**!language** - Επιλέξτε την προτιμώμενη γλώσσα σας",
                "verify": "Κάντε κλικ στο κουμπί Επαλήθευση για πρόσβαση στα κανάλια",
                "footer": "Για υποστήριξη, επικοινωνήστε με έναν διαχειριστή"
            },
            "ES": {
                "title": "🤖 Comandos de Thronos Bot",
                "description": "Aquí están todos los comandos disponibles:",
                "setup": "**!setup_server** - Configurar automáticamente canales del servidor (Solo Admin)",
                "stats": "**!stats** - Mostrar estadísticas de red en tiempo real",
                "help": "**!help [comando]** - Mostrar este mensaje de ayuda",
                "lang": "**!language** - Seleccionar su idioma preferido",
                "verify": "Haga clic en el botón Verificar para acceder a los canales",
                "footer": "Para soporte, contacte a un administrador"
            },
            "RU": {
                "title": "🤖 Команды Thronos Bot",
                "description": "Вот все доступные команды:",
                "setup": "**!setup_server** - Автоматическая настройка каналов сервера (Только Admin)",
                "stats": "**!stats** - Показать статистику сети в реальном времени",
                "help": "**!help [команда]** - Показать это справочное сообщение",
                "lang": "**!language** - Выбрать предпочитаемый язык",
                "verify": "Нажмите кнопку Проверить для доступа к каналам",
                "footer": "Для поддержки свяжитесь с администратором"
            },
            "JA": {
                "title": "🤖 Thronos Bot コマンド",
                "description": "利用可能なコマンド一覧:",
                "setup": "**!setup_server** - サーバーチャンネルの自動設定 (管理者のみ)",
                "stats": "**!stats** - リアルタイムネットワーク統計を表示",
                "help": "**!help [コマンド]** - このヘルプメッセージを表示",
                "lang": "**!language** - 優先言語を選択",
                "verify": "確認ボタンをクリックしてチャンネルにアクセス",
                "footer": "サポートについては管理者にお問い合わせください"
            }
        }
        
        text = help_data.get(lang, help_data["EN"])
        
        embed = discord.Embed(
            title=text["title"],
            description=text["description"],
            color=0x3498db
        )
        
        embed.add_field(name="📋 Commands / Εντολές / Comandos", value=(
            f"{text['setup']}\n"
            f"{text['stats']}\n"
            f"{text['help']}\n"
            f"{text['lang']}\n"
            f"{text['verify']}"
        ), inline=False)
        
        embed.set_footer(text=text["footer"])
        
        await ctx.reply(embed=embed, ephemeral=True)
        logger.info(f"Help command used by {ctx.author} in language {lang}")

async def setup(bot):
    await bot.add_cog(CustomHelp(bot))
