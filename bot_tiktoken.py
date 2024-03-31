"""

BOT_NAME="tiktoken"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
ChatGPT

"""

from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe.client
import tiktoken
from fastapi_poe import PoeBot, make_app
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import Image, Stub, asgi_app
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000


encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        last_message = query.query[-1].content
        tokens = encoding.encode(last_message)
        last_message = "\n".join(
            [
                f'"{token}": -10,  # {str(encoding.decode_single_token_bytes(token))[2:-1]}'
                for token in tokens
            ]
        )
        yield self.text_event(last_message)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={},
            allow_attachments=False,  # to update when ready
            introduction_message="Submit a statement for it to be broken down into tokens that ChatGPT reads.",
        )


bot = EchoBot()

image = Image.debian_slim().pip_install("fastapi-poe==0.0.23", "tiktoken")

stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, allow_without_key=True)
    return app
