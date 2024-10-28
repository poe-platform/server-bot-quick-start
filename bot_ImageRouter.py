"""

BOT_NAME="ImageRouter"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Sample bot that wraps GPT-3.5-Turbo but makes responses use all-caps.

"""

from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp


class ImageRouterBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        async for msg in fp.stream_request(
            request, "Playground-V2", request.access_key
        ):
            yield msg

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={"Playground-V2": 1})
