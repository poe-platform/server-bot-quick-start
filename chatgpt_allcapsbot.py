"""

Sample bot that wraps chatGPT but makes responses use all-caps.

"""
from __future__ import annotations

from typing import AsyncIterable

from fastapi_poe import PoeBot
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import QueryRequest
from sse_starlette.sse import ServerSentEvent


class ChatGPTAllCapsBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        async for msg in stream_request(query, "chatGPT", query.api_key):
            if isinstance(msg, MetaMessage):
                yield self.meta_event(
                    content_type=msg.content_type,
                    linkify=msg.linkify,
                    suggested_replies=True,
                )
                continue
            elif msg.is_suggested_reply:
                yield self.suggested_reply_event(msg.text.upper())
            elif msg.is_replace_response:
                yield self.replace_response_event(msg.text.upper())
            else:
                yield self.text_event(msg.text.upper())
