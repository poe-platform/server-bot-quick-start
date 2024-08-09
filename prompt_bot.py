"""

Sample bot that wraps Claude-3-Haiku but makes responses Haikus

"""

from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from modal import App, Image, asgi_app

SYSTEM_PROMPT = """
All your replies are Haikus.
""".strip()


class PromptBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        request.query = [
            fp.ProtocolMessage(role="system", content=SYSTEM_PROMPT)
        ] + request.query
        async for msg in fp.stream_request(
            request, "Claude-3-Haiku", request.access_key
        ):
            yield msg

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={"Claude-3-Haiku": 1})


REQUIREMENTS = ["fastapi-poe==0.0.47"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App("prompt-bot-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = PromptBot()
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
