# Welcome to the Poe API tutorial. The starter code provided provides you with a quick way to get 
# a bot running. By default, the starter code uses the EchoBot, which is a simple bot that echos
# a message back at its user and is a good starting point for your bot, but you can 
# comment/uncomment any of the following code to try out other example bots.

from fastapi_poe import run

# Echo bot is a very simple bot that just echoes back the user's last message.
from echobot import EchoBot
bot = EchoBot()

# A Sample bot that showcases the capabilities the protocol provides. Please see the 
# following link for the full set of available message commands: https://github.com/poe-platform/poe-protocol/blob/main/docs/catbot.md
# from catbot import CatBot
# bot = CatBot()

# A custom chatbot built on top of ChatGPT and LangChain.
# Add your OpenAI key here, e.g. sk-1234
# OPEN_AI_API_KEY = ""
# from langcatbot import LangCatBot
# bot = LangCatBot(OPEN_AI_API_KEY)

# Add your Poe API key here. You can go to https://poe.com/create_bot?api=1 to generate one.
POE_API_KEY = "meow" * 8
run(bot, api_key=POE_API_KEY)