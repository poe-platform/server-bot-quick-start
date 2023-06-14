"""

Sample bot that returns results from both Sage and Claude-Instant.

"""
from __future__ import annotations

from typing import AsyncIterable

from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeBot, run
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import QueryRequest


class BattleBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        for bot in ("sage", "claude-instant"):
            yield self.text_event(f"\n\n**{bot.title()}** says:\n")
            async for msg in stream_request(query, bot, "key"):
                if isinstance(msg, MetaMessage):
                    continue
                elif msg.is_suggested_reply:
                    yield self.suggested_reply_event(msg.text)
                elif msg.is_replace_response:
                    yield self.replace_response_event(msg.text)
                else:
                    yield self.text_event(msg.text)


if __name__ == "__main__":
    run(BattleBot())
