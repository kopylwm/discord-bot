import discord
import logging
import dotenv
import os

# Write the logs to a file <discord.log>
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Retrieve token from <.env>
dotenv.load_dotenv()
TOKEN = str(os.getenv('TOKEN'))