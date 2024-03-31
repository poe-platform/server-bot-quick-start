"""

BOT_NAME="TrinoAgentEx"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
download and save wine dataset
list directory

"""

import os

from fastapi_poe import make_app
from modal import Stub, asgi_app

from bot_TrinoAgent import TrinoAgentBot, image_bot

bot = TrinoAgentBot()
bot.prompt_bot = "GPT-4"
bot.iteration_count = 10

stub = Stub("poe-bot-quickstart")


@stub.function(image=image_bot)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
