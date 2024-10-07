import discord
from discord.ext import commands
import aiosqlite

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