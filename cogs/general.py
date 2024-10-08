import logging
import discord
from discord import app_commands
from discord.ext import commands
from .database import DatabaseCog
from utils import utils

# Configure logging
logging.basicConfig(level=logging.INFO,  # Change to DEBUG for more verbose output
                    format='%(asctime)s - %(levelname)s - %(message)s')

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_cog = DatabaseCog(bot)

    @app_commands.command(name="profile", description="Displays user profile")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        try:
            if member is None:
                member = interaction.user
            
            user_id = str(member.id)
            logging.info(f"[DEBUG] User ID: {user_id}")

            user_exists = await self.db_cog.ensure_user(user_id)
            logging.info(f"[DEBUG] User Exists: {user_exists}")

            user_data = await self.db_cog.fetch_user_data(user_id)
            logging.info(f"[DEBUG] User Data: {user_data}")

            # Check if user_data is None - UNDEEDED AS ensure_user sets default values            
            #if user_data is None:
                #user_data = (0, 0, 0, "")

            spent, loyalty_points, bank, last_redeem = user_data
            formatted_spent = utils.format_amount(spent)
            formatted_bank = utils.format_amount(bank)

            embed = discord.Embed(
                title=f"{member.name}'s Profile",
                color=discord.Color.red()
            )
            embed.description = (
                f"<:gold:1289649818066616371> **Total GP Spent:** {formatted_spent}\n"
                f"<:ticket:1289650551453126728> **Loyalty Points:** {loyalty_points}\n"
                f"<:gold:1289649818066616371> **Bank:** {formatted_bank}\n"
            )

            embed.set_thumbnail(url=member.avatar.url)
            embed.set_footer(text="Profile Info • Updated Now")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logging.error(f"[ERROR] Exception in profile command: {e}")
            await interaction.response.send_message(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(GeneralCog(bot))
