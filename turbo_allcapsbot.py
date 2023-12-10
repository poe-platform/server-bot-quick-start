"""

Sample bot that wraps GPT-3.5-Turbo but makes responses use all-caps.

"""
from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp


class GPT35TurboAllCapsBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        async for msg in fp.stream_request(
            request, "GPT-3.5-Turbo", request.access_key
        ):
            yield msg.model_copy(update={"text": msg.text.upper()})

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={"GPT-3.5-Turbo": 1})
