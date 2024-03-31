"""

BOT_NAME="ModelRouter"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

"""

from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from modal import Image, Stub, asgi_app


class GPT35TurboAllCapsBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        request.query = [
            {"role": "system", "content": "Reply in Spanish"},
        ] + request.query
        async for msg in fp.stream_request(
            request, "Claude-3-Opus", request.access_key
        ):
            yield msg

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies={"Claude-3-Opus": 1},
            allow_attachments=True,
        )


REQUIREMENTS = ["fastapi-poe==0.0.34"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("turbo-allcaps-poe")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    bot = GPT35TurboAllCapsBot()
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
