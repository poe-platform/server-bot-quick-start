# Welcome to the Poe API tutorial. The starter code provided provides you with a quick way to get
# a bot running. By default, the starter code uses the EchoBot, which is a simple bot that echos
# a message back at its user and is a good starting point for your bot, but you can
# comment/uncomment any of the following code to try out other example bots.

from fastapi_poe import make_app
from modal import asgi_app, Stub, Image

from echobot import EchoBot
from catbot import CatBot
from chatgpt_all_caps import ChatGPTAllCapsBot
from battle import BattleBot
from concurrent_battle import ConcurrentBattleBot


# Echo bot is a very simple bot that just echoes back the user's last message.
bot = EchoBot()

# A sample bot that showcases the capabilities the protocol provides. Please see the
# following link for the full set of available message commands:
# https://github.com/poe-platform/api-bot-tutorial/blob/main/catbot/catbot.md
# bot = CatBot()

# A bot that wraps Poe's Sage bot, but makes all messages ALL CAPS.
# bot = ChatGPTAllCapsBot()

# A bot that calls on both Sage and Claude-Instant and shows the results.
# bot = BattleBot()

# Like BattleBot, but streams both responses at once.
# bot = ConcurrentBattleBot()

# Optionally add your Poe API key here. You can go to https://poe.com/create_bot?api=1 to generate
# one. We strongly recommend adding this key for a production bot to prevent abuse,
# but the starter example disables the key check for convenience.
# POE_API_KEY = ""
# app = make_app(bot, api_key=POE_API_KEY)

image = (
    Image
    .debian_slim()
    .pip_install_from_requirements("requirements.txt")
)
stub = Stub("poe-bot-quickstart")

@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, allow_without_key=True)
    return app