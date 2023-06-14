"""

Sample bot that wraps Sage and sends all messages in all-caps.

"""
from __future__ import annotations

from typing import AsyncIterable

from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeBot, run
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import QueryRequest


class AllCapsBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        async for msg in stream_request(query, "sage", "key"):
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


if __name__ == "__main__":
    run(AllCapsBot())
