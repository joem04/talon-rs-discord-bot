import discord
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta
import random as r
import logging


# Configure logging
logging.basicConfig(
    filename='bot_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
    
token_file = 'token.env'

# Reads token file
try:
    with open(token_file, 'r') as f:
        TOKEN = f.read().strip()
except FileNotFoundError:
    logging.error(f"Token file not found: {token_file}")
    raise SystemExit(f"Token file not found: {token_file}")

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Sync / commands on bot startup
@bot.event
async def on_ready():
    try:
        synced_commands = await bot.tree.sync()
        print(f"[!] Synced {len(synced_commands)} Commands.")
    except Exception as e:
        logging.error(f"Error syncing commands: {e}")
        print("Error syncing commands.")


# Slash command to shut down the bot
@bot.tree.command(name="shutdown", description="Shut down the bot")
@commands.has_role("Admin")  # Only admins can shut down the bot
async def shutdown(interaction: discord.Interaction):
    await interaction.response.send_message("Shutting down...")
    await bot.close()


data_file = 'user_data.json'

# Opens user data file and loads in file as user_data if it exists and has valid JSON, otherwise creates it
try:
    if os.path.exists(data_file):
        if os.path.getsize(data_file) > 0:  # Check if the file is not empty
            with open(data_file, 'r') as f:
                try:
                    user_data = json.load(f)  # Try to load the JSON data
                except json.JSONDecodeError:
                    logging.error("Invalid JSON data in user data file.")
                    user_data = {}  # If JSON is invalid, initialize an empty dictionary
        else:
            user_data = {}  # If the file is empty, initialize an empty dictionary
    else:
        with open(data_file, 'a'): pass  # Create the file if it doesn't exist
        user_data = {}
except Exception as e:
    logging.error(f"Error loading user data: {e}")
    user_data = {}  # Initialize an empty dictionary if an error occurs

# Function to save user data to a file
def save_data():
    try:
        with open(data_file, 'w') as f:
            json.dump(user_data, f)
    except Exception as e:
        logging.error(f"Error saving user data: {e}")


# Function to format numeric numbers as gp cash stacks e.g. 10,0000,000 as 10m
def format_amount(amount):
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.0f}m" 
    elif amount >= 1_000:
        return f"{amount / 1_000:.0f}k"    
    else:
        return str(amount)                   


# Allows formatted amounts to be parsed in amount altering commands
def parse_amount(amount_str):
    if amount_str[-1].lower() == 'm':
        return int(float(amount_str[:-1]) * 1_000_000)
    elif amount_str[-1].lower() == 'k':
        return int(float(amount_str[:-1]) * 1_000)
    else:
        return int(amount_str)


# Slash command to display profile
@bot.tree.command(name="profile", description="Displays user profile")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    # If no user is mentioned, default to the author of the message
    if member is None:
        member = interaction.user

    user_id = str(member.id)

    # Ensure the user has an entry in user_data
    try:
        if user_id not in user_data:
            # Initialize profile and save it to user_data
            user_data[user_id] = {'spent': 0,
                                'loyalty_points': 0, 
                                'bank': 0, 
                                'last_chest_redeem': ""}  
            save_data()

        # Assigns json objects to variables
        spent = user_data[user_id]['spent']
        loyalty_points = user_data[user_id]['loyalty_points']
        bank = user_data[user_id]['bank']
        formatted_spent = format_amount(spent)
        formatted_bank = format_amount(bank)
        last_chest_redeem = user_data[user_id]['last_chest_redeem']

        # Create an embed for the profile
        embed = discord.Embed(
            title=f"{member.name}'s Profile",
            color=discord.Color.red()  # Choose a color for the embed
        )

        # Set the description with the emoji directly included
        embed.description = (
            f"<:gold:1289649818066616371> **Total GP Spent:** {formatted_spent}\n"  # Replace with actual emoji ID
            f"<:ticket:1289650551453126728> **Loyalty Points:** {loyalty_points}\n"
            f"<:gold:1289649818066616371> **Bank:** {formatted_bank}\n"  # Replace with actual emoji ID
        )

        # Set the thumbnail using the user's avatar
        embed.set_thumbnail(url=member.avatar.url)  # Use .avatar to get the URL

        # Set footer
        embed.set_footer(text="Profile Info • Updated Now")

        # Send the embed to the channel
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logging.error(f"Error displaying profile: {e}")
        await interaction.response.send_message(f"Error displaying profile: {e}")


# Slash command for setting order status to paid and everything included.
@bot.tree.command(name="paid", description="Mark an order as paid and move the ticket.")
@commands.has_role("Admin")
async def paid(interaction: discord.Interaction, amount: str, member: discord.Member = None, order_note: str = None):
    if member is None:
        member = interaction.user  # Default to the author if no member is mentioned

    user_id = str(member.id)

    # Ensure user has an entry in user_data
    try:
        if user_id not in user_data:
            user_data[user_id] = {'spent': 0, 'loyalty_points': 0}
            save_data()

        # Parse and add the amount
        amount_value = parse_amount(amount)
        user_data[user_id]['spent'] += amount_value

        # Calculate loyalty points gained
        loyalty_points_gained = amount_value // 10_000_000  # 1 point per 10m
        user_data[user_id]['loyalty_points'] += loyalty_points_gained
        save_data()

        # Check if the member has the "Customer" role
        customer_role = discord.utils.get(interaction.guild.roles, name="Customer")
        if customer_role and customer_role not in member.roles:
            try:
                await member.add_roles(customer_role)
            except discord.Forbidden as e:
                logging.error(f"No access to add role: {e}")
                await interaction.response.send_message(f"No access to add role: {e}", ephemeral=True)
                return
            except discord.HTTPException as e:
                logging.error(f"Failed to assign the 'Customer' role. Error: {e}")
                await interaction.response.send_message(f"Failed to assign the 'Customer' role. Please contact an Admin: {e}", ephemeral=True)
                return

        paid_category_id = 1289320593472229428  # Adjust with your actual category ID

        # Get the target category object
        paid_category = discord.utils.get(interaction.guild.categories, id=paid_category_id)
        try:
            await interaction.channel.edit(category=paid_category)
        except discord.Forbidden:
            logging.error("No permission to move the channel.")
            await interaction.response.send_message("No permission to move the channel.", ephemeral=True)
            return
        except discord.HTTPException as e:
            logging.error(f"Failed to move the channel: {e}")
            await interaction.response.send_message(f"Failed to move the channel: {e}", ephemeral=True)
            return

        # Get current ticket number via channel name
        ticket_number = interaction.channel.name

        # Create the embed for the order status set to paid
        embed = discord.Embed(
            title=f"Order: {ticket_number[7:]}",
            color=discord.Color.red()
        )

        embed.description = (
            f":white_check_mark: Order Status: **Paid / Order Pending Delivery**\n"
            f":moneybag: Buyer: **{member}**\n"
            f"<:gold:1289649818066616371> Amount: **{amount}**\n"
            f":notepad_spiral: Order Description: {order_note}\n"
            "\n"
            "Thank you so much for your order! Please be patient whilst we assign a worker."
        )

        embed.set_footer(text="Order Info • Updated Now")

        # Add the gif as a thumbnail using the correct path reference
        embed.set_thumbnail(url="attachment://paid.gif")

        # Send the paid embed and attach the GIF with the file argument
        paid_gif = discord.File("attachments/paid.gif", filename="paid.gif")
        
        # Respond to the interaction with the embed and file
        await interaction.response.send_message(embed=embed, file=paid_gif)

        # Retrieve the message that was just sent
        paid_embed_message = await interaction.original_response()

        # Pin the message after sending it
        await paid_embed_message.pin()

        # Send Order embed to worker channel
        worker_channel_id = 1290661812945158195  # Adjust with your actual worker channel ID
        worker_channel = interaction.guild.get_channel(worker_channel_id)
        worker_role = discord.utils.get(interaction.guild.roles, name="Worker")

        if worker_channel:
            thread = await worker_channel.create_thread(
                name=f"Order Thread: {ticket_number[7:]}",
                auto_archive_duration=60,
            )
            await thread.send(f"{worker_role.mention} | Please ask any additional questions you need about this job. Jobs are first come, first serve.")
            await thread.send("Please don't accept any jobs you are unable to complete for the buyer.")
            await thread.send(embed=embed)

    except Exception as e:
        logging.error(f"Error in /paid command: {e}")
        await interaction.response.send_message("An error occurred while processing the payment. Please try again later.", ephemeral=True)


# Slash command to assign worker to ticket channel
@bot.tree.command(name="worker", description="Assign worker to a ticket")
@commands.has_role("Admin")
async def worker(interaction: discord.Interaction, worker: discord.Member):
    # Get the current thread (the context's channel)
    thread = interaction.channel

    # Ensure the command is called from a thread
    if not isinstance(thread, discord.Thread):
        await interaction.response.send_message("This command can only be used in a thread.")
        return

    # Extract the ticket number from the thread name (assuming the format "Order: {ticket_number}")
    try:
        ticket_number = thread.name.split(": ")[1]  # Extract the number after "Order: "
    except IndexError:
        await interaction.response.send_message("Could not find a valid ticket number in the thread name.")
        return

    # Find the channel with the matching ticket number
    ticket_channel_name = f"ticket-{ticket_number}"
    ticket_channel = discord.utils.get(interaction.guild.text_channels, name=ticket_channel_name)

    # Ensure the channel was found
    if ticket_channel is None:
        await interaction.response.send_message(f"Could not find a ticket channel with the name: {ticket_channel_name}.")
        return

    # Check if the member has the Worker role
    worker_role = discord.utils.get(interaction.guild.roles, name="Worker")
    if worker_role not in worker.roles:
        await interaction.response.send_message(f"{worker.mention} does not have the role: {worker_role.mention}")
        return

    # Assign permissions to the worker for the ticket channel
    try:
        await ticket_channel.set_permissions(worker, read_messages=True, send_messages=True, read_message_history=True)
    except discord.Forbidden as e:
        logging.error(f"Forbidden error assigning permissions for {worker.mention} in {ticket_channel.name}: {e}")
        await interaction.response.send_message("No permission to assign roles in the ticket channel.", ephemeral=True)
        return
    except discord.HTTPException as e:
        logging.error(f"HTTPException assigning permissions for {worker.mention} in {ticket_channel.name}: {e}")
        await interaction.response.send_message("Failed to assign permissions. Please try again.", ephemeral=True)
        return

    # Notify the worker and update the ticket channel
    try:
        await ticket_channel.send(f"{worker.mention} has been assigned to {ticket_channel.mention}")
    except discord.HTTPException as e:
        logging.error(f"Error notifying {worker.mention} in {ticket_channel.name}: {e}")
        await interaction.response.send_message("Failed to notify the worker. Please try again.", ephemeral=True)
        return

    # Optionally delete the thread after assigning the worker
    await thread.delete()


# Slash command to add loyalty points to a user
@bot.tree.command(name="add_lp", description="Add loyalty points to a user")
@commands.has_role("Admin")  # Only admins can add loyalty points
async def add_lp(interaction: discord.Interaction, points: int, member: discord.Member = None):
    if member is None:
        member = interaction.user  # Default to the author if no member is mentioned

    user_id = str(member.id)

    # Ensure the user has an entry in user_data
    if user_id not in user_data:
        user_data[user_id] = {'spent': 0, 'loyalty_points': 0}
        save_data()

    # Add the loyalty points to the user's profile
    try:
        user_data[user_id]['loyalty_points'] += points
        save_data()
        await interaction.response.send_message(f"Added {points} loyalty points to {member.mention}'s profile!")
    except Exception as e:
        logging.error(f"Error adding loyalty points to {member.mention}: {e}")
        await interaction.response.send_message("Failed to add loyalty points. Please try again.", ephemeral=True)

# Slash command to subtract loyalty points from a user
@bot.tree.command(name="subtract_lp", description="Subtract loyalty points from a user")
@commands.has_role("Admin")  # Only admins can subtract loyalty points
async def subtract_lp(interaction: discord.Interaction, points: int, member: discord.Member = None):
    if member is None:
        member = interaction.user  # Default to the author if no member is mentioned

    user_id = str(member.id)

    # Ensure the user has an entry in user_data
    if user_id not in user_data:
        user_data[user_id] = {'spent': 0, 'loyalty_points': 0}
        save_data()

    # Subtract the loyalty points from the user's profile
    try:
        user_data[user_id]['loyalty_points'] -= points
        save_data()
        await interaction.response.send_message(f"Subtracted {points} loyalty points from {member.mention}'s profile!")
    except Exception as e:
        logging.error(f"Error subtracting loyalty points from {member.mention}: {e}")
        await interaction.response.send_message("Failed to subtract loyalty points. Please try again.", ephemeral=True)


# Slash command to add an amount to a user's bank
@bot.tree.command(name="add_bank", description="Add an amount to a user's bank")
@commands.has_role("Admin")  # Only admins can add to the bank
async def add_bank(interaction: discord.Interaction, amount: str, member: discord.Member = None):
    if member is None:
        member = interaction.user  # Default to the author if no member is mentioned

    user_id = str(member.id)

    # Ensure the user has an entry in user_data
    if user_id not in user_data:
        user_data[user_id] = {'spent': 0, 'loyalty_points': 0, 'bank': 0}
        save_data()

    # Parse and add the amount to the user's bank
    try:
        amount_value = parse_amount(amount)
        user_data[user_id]['bank'] += amount_value
        save_data()
        await interaction.response.send_message(f"Added {format_amount(amount_value)} to {member.mention}'s bank!")
    except Exception as e:
        logging.error(f"Error adding bank amount to {member.mention}: {e}")
        await interaction.response.send_message("Failed to add to bank. Please try again.", ephemeral=True)


# Slash command to subtract an amount from a user's bank
@bot.tree.command(name="subtract_bank", description="Subtract an amount from a user's bank")
@commands.has_role("Admin")  # Only admins can subtract from the bank
async def subtract_bank(interaction: discord.Interaction, amount: str, member: discord.Member = None):
    if member is None:
        member = interaction.user  # Default to the author if no member is mentioned

    user_id = str(member.id)

    # Ensure the user has an entry in user_data
    if user_id not in user_data:
        user_data[user_id] = {'spent': 0, 'loyalty_points': 0, 'bank': 0}
        save_data()

    # Parse and subtract the amount from the user's bank
    try:
        amount_value = parse_amount(amount)
        user_data[user_id]['bank'] -= amount_value
        save_data()
        await interaction.response.send_message(f"Subtracted {format_amount(amount_value)} from {member.mention}'s bank!")
    except Exception as e:
        logging.error(f"Error subtracting bank amount from {member.mention}: {e}")
        await interaction.response.send_message("Failed to subtract from bank. Please try again.", ephemeral=True)


# Command to give users a random amount of gp assigned to their bank in their user data
@bot.tree.command(name='daily', description='Daily chest command')
async def daily(interaction: discord.Interaction):
    # Set variables
    user_id = str(interaction.user.id)

    # Ensure the user has an entry in user_data
    if user_id not in user_data:
        user_data[user_id] = {
            'spent': 0,
            'loyalty_points': 0,
            'bank': 0,
            'last_chest_redeem': ""  # Initialize to empty string
        }

    # Retrieve the last redeem time, ensuring it's safe to access
    last_redeem_time = user_data[user_id]['last_chest_redeem']
    current_time = str(datetime.now())[0:19]

    try:
        # If last redeem date is not the same as the current date then allow daily command
        if str(last_redeem_time)[0:10] != current_time[0:10]:  # Use [0:10] for date comparison
            user_data[user_id]['last_chest_redeem'] = current_time

            # Add a random amount to the user's bank
            amount = r.randint(20000, 100000)
            user_data[user_id]['bank'] += amount  # Directly add to bank
            save_data()

            await interaction.response.send_message(f"You have received {amount} GP in your bank!")
        else:
            # Trim fractional part if it exists before converting to datetime
            last_redeem = datetime.strptime(last_redeem_time[:19], "%Y-%m-%d %H:%M:%S")

            # Convert the current_time string back to a datetime object for calculations
            current_time_dt = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")

            # Calculate time until midnight for next redeem
            next_day = datetime.combine(current_time_dt.date(), datetime.min.time()) + timedelta(days=1)
            time_until_midnight = next_day - current_time_dt

            # Calculate hours and minutes until the next day
            hours, remainder = divmod(time_until_midnight.seconds, 3600)
            minutes, _ = divmod(remainder, 60)

            await interaction.response.send_message(
                f"You can't redeem a daily chest for another {hours} hours and {minutes} minutes."
            )
    except Exception as e:
        logging.error(f"Error processing daily command for {interaction.user.mention}: {e}")
        await interaction.response.send_message("An error occurred while processing your daily chest. Please try again later.", ephemeral=True)


if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except discord.LoginFailure as e:
        logging.critical("Login failed: Please check your bot token. Error: %s", e)
        print("Login failed: Please check your bot token.")
    except Exception as e:
        logging.critical("An unexpected error occurred while running the bot: %s", e)
        print("An unexpected error occurred. Please check the logs.")

