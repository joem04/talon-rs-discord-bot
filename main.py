import discord
from discord.ext import commands
import json
import os

token_file = 'token.env'

# Reads token file
with open(token_file, 'r') as f:
    TOKEN = f.read().strip()

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())


# !shutdown command - throws error dont worry!
@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    exit()


data_file = 'user_data.json'

# Opens user data file and loads in file as user_data if it exists and has valid JSON, otherwise creates it
if os.path.exists(data_file):
    if os.path.getsize(data_file) > 0:  # Check if the file is not empty
        with open(data_file, 'r') as f:
            try:
                user_data = json.load(f)  # Try to load the JSON data
            except json.JSONDecodeError:
                user_data = {}  # If JSON is invalid, initialize an empty dictionary
    else:
        user_data = {}  # If the file is empty, initialize an empty dictionary
else:
    with open(data_file, 'a'): pass  # Create the file if it doesn't exist
    user_data = {}



# Function to save user data to a file
def save_data():
    with open(data_file, 'w') as f:
        json.dump(user_data, f)


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


# Displays profile, initializes if it doesn't exist
@bot.command()
async def profile(ctx, member: discord.Member = None):
    # If no user is mentioned, default to the author of the message
    if member is None:
        member = ctx.author

    user_id = str(member.id)

    # Ensure the user has an entry in user_data
    if user_id not in user_data:
        user_data[user_id] = {'spent': 0, 'loyalty_points': 0}  # Initialize profile sand save it to user_data
        save_data()

    spent = user_data[user_id]['spent']
    loyalty_points = user_data[user_id]['loyalty_points']
    formatted_spent = format_amount(spent)

    # Create an embed for the profile
    embed = discord.Embed(
        title=f"{member.name}'s Profile",
        color=discord.Color.red()  # Choose a color for the embed
    )

    # Set the description with the emoji directly included
    embed.description = (
        f"<:gold:1289649818066616371> **Total GP Spent:** {formatted_spent}\n"  # Replace with actual emoji ID
        f"<:ticket:1289650551453126728> **Loyalty Points:** {loyalty_points}"
    )

    # Set the thumbnail using the user's avatar
    embed.set_thumbnail(url=member.avatar.url)  # Use .avatar to get the URL

    # Set footer
    embed.set_footer(text="Profile Info • Updated Now")

    # Send the embed to the channel
    await ctx.send(embed=embed)


# !paid command to set order status to paid, and every operation associated with it
@bot.command()
@commands.has_role("Admin")  # Only admins can alter profiles
async def paid(ctx, amount: str, member: discord.Member=None, *, order_note: str):
    if member is None:
        member = ctx.author  # Default to the author if no member is mentioned

    user_id = str(member.id)

    # Ensure user has an entry in user_data
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
    customer_role = discord.utils.get(ctx.guild.roles, name="Customer")

    # If the member doesn't have the "Customer" role, assign it
    if customer_role not in member.roles:
        try:
            await member.add_roles(customer_role)
        except discord.Forbidden as e:
            await ctx.send(f"No access: {e}")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to assign the 'Customer' role. Please contact an Admin: {e}")

    paid_category_id = 1289320593472229428  

    # Get the target category object
    paid_category = discord.utils.get(ctx.guild.categories, id=paid_category_id)

    # Move the current channel to the target category
    try:
        await ctx.channel.edit(category=paid_category)
    
    # Handle errors
    except discord.Forbidden:
        await ctx.send("No permission to move the channel.")
    except discord.HTTPException as e:
        await ctx.send(f"Failed to move the channel: {e}")

    # Get current ticket number via channel name
    ticket_number = ctx.channel.name

    # File upload for paid thumbnail for the embed
    paid_gif = discord.File("attachments/paid.gif", filename="paid.gif")

    # Create embed message for order status set to paid
    embed = discord.Embed(
    title= f"Order: {ticket_number[7:]}" ,
    color=discord.Color.red()  
)
    
    embed.description = (
    f":white_check_mark: Order Status: **Paid / Order Pending Delivery**\n" 
    f":moneybag: Buyer: **{member}**\n"
    f"<:gold:1289649818066616371> Amount: **{amount}**\n"
    f":notepad_spiral: Order Description: {order_note}\n"
    "\n"
    f"Thank you so much for your order! Please be patient whilst we assign a worker."
)
    embed.set_thumbnail(url="attachment://paid.gif") 

    embed.set_footer(text="Order Info • Updated Now")

    # Send the embed and assign it to a variable
    paid_embed_message = await ctx.send(embed=embed, file=paid_gif)

    # Pin message after sent
    await paid_embed_message.pin()

    # Send Order embed to worker channel
    worker_channel_id = 1290661812945158195
    worker_channel = ctx.guild.get_channel(worker_channel_id)
    worker_role = discord.utils.get(ctx.guild.roles, name="Worker")

    # Start a thread in the target channel and send the embed
    thread = await worker_channel.create_thread(
        name=f"Order Thread: {ticket_number[7:]}",
        auto_archive_duration=60,
        ) 
    
    await thread.send(f"{worker_role.mention} | Please ask any additional questions you need about this job. Jobs are first come first serve. ")
    await thread.send("Please dont accept any jobs you are unable to complete for the buyer.")
    await thread.send(embed=embed)  


# Command to assign worker to ticket channel
@bot.command()
@commands.has_role("Admin")
async def worker(ctx, worker: discord.Member):
    # Get the current thread (the context's channel)
    thread = ctx.channel

    # Ensure the command is called from a thread
    if not isinstance(thread, discord.Thread):
        await ctx.send("This command can only be used in a thread.")
        return

    # Extract the ticket number from the thread name (assuming the format "Order: {ticket_number}")
    try:
        ticket_number = thread.name.split(": ")[1]  # Extract the number after "Order: "
    except IndexError:
        await ctx.send("Could not find a valid ticket number in the thread name.")
        return

    # Find the channel with the matching ticket number
    ticket_channel_name = f"ticket-{ticket_number}"
    ticket_channel = discord.utils.get(ctx.guild.text_channels, name=ticket_channel_name)

    # Ensure the channel exists
    if ticket_channel is None:
        await ctx.send(f"Could not find a ticket channel with the name: {ticket_channel_name}.")
        return

    # Check if the mentioned user has the "Worker" role
    worker_role = discord.utils.get(ctx.guild.roles, name="Worker")
    if worker_role not in worker.roles:
        await ctx.send(f"{worker.mention} does not have the role: {worker_role.mention}")
        return

    # Set permissions for the worker in the ticket channel
    await ticket_channel.set_permissions(worker, read_messages=True, send_messages=True, read_message_history=True)
    await ticket_channel.send(f"{worker.mention} has been assigned to {ticket_channel.mention}")

    await thread.delete()
    

# Command to add loyalty points
@bot.command()
@commands.has_role("Admin")  # Only admins can alter profiles
async def add_lp(ctx, amount: int, member: discord.Member):
    user_id = str(member.id)

    # Ensure the user has an entry in user_data
    if user_id not in user_data:
        user_data[user_id] = {'spent': 0, 'loyalty_points': 0}

    user_data[user_id]['loyalty_points'] += amount
    save_data()

    await ctx.send(f"Added {amount} loyalty points to {member.name}. Total: {user_data[user_id]['loyalty_points']}")


# Command to subtract loyalty points
@bot.command()
@commands.has_role("Admin")  # Only admins can alter profiles
async def subtract_lp(ctx, amount: int, member: discord.Member):
    user_id = str(member.id)

    # Ensure the user has an entry in user_data
    if user_id not in user_data:
        user_data[user_id] = {'spent': 0, 'loyalty_points': 0}

    user_data[user_id]['loyalty_points'] -= amount
    save_data()

    await ctx.send(f"Subtracted {amount} loyalty points from {member.name}. Total: {user_data[user_id]['loyalty_points']}")


bot.run(TOKEN)
