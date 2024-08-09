"""

Sample bot that shows the query sent to the bot.

"""

from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from devtools import PrettyFormat
from modal import App, Image, asgi_app

pformat = PrettyFormat(width=85)


class LogBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        yield fp.PartialResponse(text="```python\n" + pformat(request) + "\n```")

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            allow_attachments=True, enable_image_comprehension=True
        )


REQUIREMENTS = ["fastapi-poe==0.0.47", "devtools==0.12.2"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App("log-bot-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = LogBot()
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter examples disable the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    # POE_ACCESS_KEY = ""
    # app = make_app(bot, access_key=POE_ACCESS_KEY)
    app = fp.make_app(bot, allow_without_key=True)
    return app
