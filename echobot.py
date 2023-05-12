"""

Sample bot that echoes back messages.

"""
from __future__ import annotations

from typing import AsyncIterable

from fastapi_poe import PoeBot, run
from fastapi_poe.types import QueryRequest
from sse_starlette.sse import ServerSentEvent


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        last_message = query.query[-1].content
        yield self.text_event(last_message)


if __name__ == "__main__":
    run(EchoBot())
