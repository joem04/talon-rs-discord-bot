import discord
from discord import app_commands
from .database import DatabaseCog  # Import the DatabaseCog for database access

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_cog = DatabaseCog(bot)  # Create an instance of DatabaseCog


    # Slash command to display profile
    @app_commands.command(name="profile", description="Displays user profile")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        # If no user is mentioned, default to the author of the message
        if member is None:
            member = interaction.user

        user_id = str(member.id)

        # Ensure the user has an entry in the database
        user_exists = await self.db_cog.ensure_user(user_id)

        # Fetch user data from the database
        user_data = await self.db_cog.fetch_user_data(user_id)

        # If no data is found, it means the user was just added
        if user_data is None:
            user_data = (0, 0, 0, "")  # Default values for new users

        # Unpack user data
        spent, loyalty_points, bank, last_redeem = user_data

        # Format the amounts (if you have a format_amount function)
        formatted_spent = format_amount(spent)
        formatted_bank = format_amount(bank)

        # Create an embed for the profile
        embed = discord.Embed(
            title=f"{member.name}'s Profile",
            color=discord.Color.red()
        )

        # Set the description with the emoji directly included
        embed.description = (
            f"<:gold:1289649818066616371> **Total GP Spent:** {formatted_spent}\n"
            f"<:ticket:1289650551453126728> **Loyalty Points:** {loyalty_points}\n"
            f"<:gold:1289649818066616371> **Bank:** {formatted_bank}\n"
        )

        # Set the thumbnail using the user's avatar
        embed.set_thumbnail(url=member.avatar.url)

        # Set footer
        embed.set_footer(text="Profile Info • Updated Now")

        # Send the embed to the channel
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(GeneralCog(bot))
