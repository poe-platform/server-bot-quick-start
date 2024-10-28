"""

BOT_NAME="ModelRouter"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

"""

from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp


class ModelRouterBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        # request.query = [
        #     fp.ProtocolMessage(role="system", content="Reply in Spanish")
        # ]
        async for msg in fp.stream_request(request, "GPT-4o", request.access_key):
            yield msg

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies={"GPT-4o": 1}, allow_attachments=True
        )

