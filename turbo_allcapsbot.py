"""

Sample bot that wraps GPT-3.5-Turbo but makes responses use all-caps.

To update the dependencies, please run
curl -X POST https://api.poe.com/bot/fetch_settings/<botname>/<access_key>

"""
from __future__ import annotations

from typing import AsyncIterable

from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import stream_request
from fastapi_poe.types import (
    PartialResponse,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
from modal import Image, Stub, asgi_app


class GPT35TurboAllCapsBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        async for msg in stream_request(request, "GPT-3.5-Turbo", request.access_key):
            yield msg.model_copy(update={"text": msg.text.upper()})

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(server_bot_dependencies={"GPT-3.5-Turbo": 1})


bot = GPT35TurboAllCapsBot()

# The following is setup code that is required to host with modal.com
image = Image.debian_slim().pip_install("fastapi_poe==0.0.23")
stub = Stub("poe-server-bot-quick-start")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter example disables the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    # POE_ACCESS_KEY = ""
    # app = make_app(bot, access_key=POE_ACCESS_KEY)
    app = make_app(bot, allow_without_key=True)
    return app
