import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from .database import DatabaseCog
import logging
from utils import utils
from settings import PAID_CATEGORY_ID, WORKER_CHANNEL_ID

# Configure logging
logging.basicConfig(level=logging.INFO,  # Change to DEBUG for more verbose output
                    format='%(asctime)s - %(levelname)s - %(message)s')


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_cog = DatabaseCog(bot)    

    @app_commands.command(name="paid", description="Sets user order status to paid")
    async def paid(self, interaction: discord.Interaction, amount: str, member: discord.Member, order_note: str = None):
        user_id = str(member.id)
        logging.info(f"Received paid command from {interaction.user.name} for user {member.name} with amount {amount}")

        try:
            # Ensure user exists in the database
            user_exists = await self.db_cog.ensure_user(user_id)
            logging.info(f"Ensured user {member.name} exists in the database.")

            # Parse the amount entry to usable data
            amount_value = utils.parse_amount(amount)
            logging.info(f"Parsed amount {amount} to {amount_value} for user {member.name}.")

            # Fetch and update user data
            user_data = await self.db_cog.fetch_user_data(user_id)
            new_spent = user_data[0] + amount_value
            user_updated = await self.db_cog.update_user_data(user_id, 'spent', new_spent)

            if user_updated:
                logging.info(f"Updated {member.name}'s spent amount to {new_spent}")
                await interaction.response.defer() # Defer this respone as would be pinned later - maybe make emphermal??
            else:
                logging.error(f"Failed to update {member.name}'s spent amount")
                await interaction.response.send_message(f"Failed to update {member.name}'s spent amount")
                return

            # Assign 'Customer' role if needed
            customer_role = discord.utils.get(member.guild.roles, name='Customer')
            if customer_role and customer_role not in member.roles:
                try:
                    await member.add_roles(customer_role)
                    logging.info(f"Assigned 'Customer' role to {member.name}.")
                except discord.Forbidden as e:
                    logging.error(f"Error adding 'Customer' role to {member.name}: {e}")
                    if not interaction.response.is_done():
                        await interaction.response.defer(f"An error occurred: {str(e)}", ephemeral=True)
                    else:
                        await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
                    return

            # Move channel to paid category
            paid_category = discord.utils.get(interaction.guild.categories, id=PAID_CATEGORY_ID)
            if paid_category:
                try:
                    await interaction.channel.edit(category=paid_category)
                    logging.info(f"Moved channel to PAID_CATEGORY for {member.name}.")
                except discord.Forbidden:
                    logging.error(f"No permission to move the channel for {member.name}.")
                    if not interaction.response.is_done():
                        await interaction.response.send_message("No permission to move the channel.", ephemeral=True)
                    else:
                        await interaction.followup.send("No permission to move the channel.", ephemeral=True)
                    return
                except discord.HTTPException as e:
                    logging.error(f"Failed to move the channel for {member.name}: {e}")
                    if not interaction.response.is_done():
                        await interaction.response.send_message(f"Failed to move the channel: {e}", ephemeral=True)
                    else:
                        await interaction.followup.send(f"Failed to move the channel: {e}", ephemeral=True)
                    return

            # Create and send embed with the paid message
            embed = discord.Embed(
                title=f"Order: {interaction.channel.name[7:]}",
                color=discord.Color.red(),
                description=f":white_check_mark: Order Status: **Paid / Order Pending Delivery**\n"
                            f":moneybag: Buyer: **{member}**\n"
                            f"<:gold:1289649818066616371> Amount: **{amount}**\n"
                            f":notepad_spiral: Order Description: {order_note}\n"
                            "Thank you for your order! Please wait while we assign a worker."
            )
            embed.set_footer(text="Order Info • Updated Now")
            embed.set_thumbnail(url="attachment://paid.gif")
            paid_gif = discord.File("attachments/paid.gif", filename="paid.gif")

            await interaction.followup.send(embed=embed, file=paid_gif)
            logging.info(f"Sent payment confirmation embed for {member.name}.")

            # Pin the message
            paid_embed_message = await interaction.original_response()
            await paid_embed_message.pin()
            logging.info(f"Pinned the payment confirmation message for {member.name}.")

            # Notify worker channel
            worker_channel = interaction.guild.get_channel(WORKER_CHANNEL_ID)
            worker_role = discord.utils.get(interaction.guild.roles, name="Worker")
            if worker_channel:
                thread = await worker_channel.create_thread(
                    name=f"Order Thread: {interaction.channel.name[7:]}",
                    auto_archive_duration=60,
                )
                await thread.send(f"{worker_role.mention} | Job details:", embed=embed)
                logging.info(f"Created a worker thread for order {interaction.channel.name[7:]}.")

        except Exception as e:
            logging.error(f"Error in /paid command: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred while processing the payment. Please try again later.", ephemeral=True)
            else:
                await interaction.followup.send("An error occurred while processing the payment. Please try again later.", ephemeral=True)

            # Fix all responses - dont really need fixed rn - not priority


    @app_commands.command(name="worker", description="Assigns worker to an order")
    @commands.has_role("Admin")
    async def worker(self, interaction: discord.Interaction, worker: discord.Member):
        # Get the current thread    

        thread = interaction.channel

        # Ensure the command is called from a thread
        if not isinstance(thread, discord.Thread):
            await interaction.response.send_message("This command can only be used in a thread.", ephemeral=True)
            return
        
        # Extract the ticked number from the thread name (assuming the format "Order: {ticket_number}")
        try:
            ticket_number = thread.name.split(": ")[1] # Space after colon
        except IndexError:
            await interaction.response.send_message("Failed to extract ticket number from the thread name.", ephemeral=True)
            return
        
        # Find the channel with the matching ticket number
        ticket_channel = discord.utils.get(interaction.guild.channels, name=f"ticket-{ticket_number}")

        # Ensure the ticket channel exists
        if ticket_channel is None:
            await interaction.response.send_message("Failed to find the ticket channel.", ephemeral=True)
            return

        # Check if assigned member is a worker
        worker_role = discord.utils.get(interaction.guild.roles, name="Worker")
        if worker_role not in worker.roles:
            await interaction.response.send_message("The assigned member is not a worker.", ephemeral=True)
            return
        
            # Assign permissions to the worker for the ticket channel
        try:
            await ticket_channel.send(f"{worker.mention} has been assigned to this order.")
        except discord.Forbidden:
            await interaction.response.send_message("Failed to assign worker to the ticket channel.", ephemeral=True)
            return
        
        # Delete thread after worker assignment - keeps the channel clean
        await thread.delete()
            

async def setup(bot):
    await bot.add_cog(AdminCog(bot))





