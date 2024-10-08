import discord
from discord.ext import commands
import aiosqlite
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,  # Change to DEBUG for more verbose output
                    format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_name = 'user_data.db'

    
    # Initalise table
    async def init_db(self):
        async with aiosqlite.connect(self.db_name) as db:
            # Create cursor
            async with db.cursor() as cursor:
                # Create table for user data
                await cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_data (
                        user_id TEXT PRIMARY KEY,
                        spent INTEGER DEFAULT 0,
                        loyalty_points INTEGER DEFAULT 0,
                        bank INTEGER DEFAULT 0,
                        last_redeem TEXT DEFAULT ''
                    )
                ''')
                # Commit creation to db file
                await db.commit()
                logging.info("[✓] User data table loaded successfully.")


    # Ensure the current user has an entry in the database
    async def ensure_user(self, user_id, spent=0, loyalty_points=0, bank=0, last_redeem=''): # Set default values
        async with aiosqlite.connect(self.db_name) as db:
            async with db.cursor() as cursor:
                # Check if the user already has an entry
                await cursor.execute('SELECT user_id FROM user_data WHERE user_id = ?', (user_id,))
                result = await cursor.fetchone()

                # If no entry exists, insert a new one
                if result is None:
                    await cursor.execute('''
                        INSERT INTO user_data (user_id, spent, loyalty_points, bank, last_redeem)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, spent, loyalty_points, bank, last_redeem))
                    await db.commit()
                    return True  # New entry created
                return False  # Entry already exists
            
    
    # Fetch user data from the database
    async def fetch_user_data(self, user_id):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.cursor() as cursor:
                await cursor.execute('SELECT spent, loyalty_points, bank, last_redeem FROM user_data WHERE user_id = ?', (user_id,))
                return await cursor.fetchone()
            

async def setup(bot):
    await bot.add_cog(DatabaseCog(bot))     