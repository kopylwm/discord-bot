# Pycord libraries
import discord
import logging
from discord.ext import commands

# Other libraries
import dotenv
import os

def main():
    # Write logs to a <discord.log> file
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    # Retrieve token from <.env> file
    dotenv.load_dotenv()
    TOKEN = os.getenv('TOKEN')

    # Enable necessary intents
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix='?', intents=intents)

    @bot.event
    async def on_ready():
        print(f'{bot.user} is ready!')

    # Add all commands
    bot.load_extension('cogs.music')
    
    bot.run(TOKEN)

if __name__ == '__main__':
    main()
