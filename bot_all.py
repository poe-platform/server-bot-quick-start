# TODO - write script to update settings

from __future__ import annotations
import os

import fastapi_poe as fp
from modal import App, Image, asgi_app

from wrapper_bot import WrapperBot
from bot_CafeMaid import EchoBot

REQUIREMENTS = ["fastapi-poe==0.0.48", "openai"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .env(
        {
            "POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"],
            "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
        }
    )
)
app = App("wrapper-bot-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    POE_ACCESS_KEY = os.environ["POE_ACCESS_KEY"]
    # see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
    # app = fp.make_app(bot, access_key=POE_ACCESS_KEY, bot_name=<YOUR_BOT_NAME>)
    app = fp.make_app(
        [
            WrapperBot(path="/WrapperBot", access_key=POE_ACCESS_KEY),
            EchoBot(path="/EchoBot", access_key=POE_ACCESS_KEY),
        ],
    )
    return app
