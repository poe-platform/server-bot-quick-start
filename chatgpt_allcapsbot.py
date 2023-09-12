"""

Sample bot that wraps ChatGPT but makes responses use all-caps.

"""
from __future__ import annotations

from typing import AsyncIterable

from fastapi_poe import PoeBot
from fastapi_poe.client import stream_request
from fastapi_poe.types import (
    PartialResponse,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)


class ChatGPTAllCapsBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[PartialResponse]:
        async for msg in stream_request(query, "ChatGPT", query.access_key):
            yield msg.model_copy(update={"text": msg.text.upper()})

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(server_bot_dependencies={"ChatGPT": 1})
