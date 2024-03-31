"""

BOT_NAME="DALL-E-3-HD-mirror"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
cat

"""

import importlib
import os

from fastapi_poe import make_app
from modal import Dict, Stub, asgi_app

module = importlib.import_module("bot_DALL-E-3-mirror")
DALLE3Bot = module.DALLE3Bot
image = module.image

GLOBAL_RATE_LIMIT_DICT_KEY = "dalle3-mirror-limit-"

stub = Stub("poe-bot-quickstart")
stub.my_dict = Dict.new()

bot = DALLE3Bot()
bot.image_quality = "hd"


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
