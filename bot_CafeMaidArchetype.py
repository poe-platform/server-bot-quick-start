"""

BOT_NAME="CafeMaidArchetype"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

"""

from __future__ import annotations

import os
from typing import AsyncIterable

from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import stream_request
from fastapi_poe.types import (
    PartialResponse,
    ProtocolMessage,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
from modal import Image, Stub, asgi_app

PROMPT_TEMPLATE = """
My prompt has full detail so no need to add more:
Style: anime
Perspective: front view
Personality: welcoming and endering
Appearance: peach-colored hair flowing down to her shoulders styled in soft curls, sparkling blue eyes and light skin.
Outfit: a traditional maid outfit consisting of a black dress accentuated with white frills and a white apron and matching black and white headdress
Action: {action}
""".strip()


class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        last_message = request.query[-1].content
        print(last_message)
        request.query = [
            ProtocolMessage(
                role="user", content=PROMPT_TEMPLATE.format(action=last_message)
            )
        ]
        async for msg in stream_request(request, "DALL-E-3", request.access_key):
            yield msg

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(server_bot_dependencies={"DALL-E-3": 1})


image = (
    Image.debian_slim()
    .pip_install("fastapi-poe==0.0.23")
    .env({"POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"]})
)

stub = Stub("poe-bot-quickstart")

bot = EchoBot()


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, allow_without_key=True)
    return app
