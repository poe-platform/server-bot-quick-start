"""

Sample bot that returns interleaved results from GPT-3.5-Turbo and Claude-instant.

"""

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from typing import AsyncIterable, AsyncIterator

import fastapi_poe as fp
from modal import App, Image, asgi_app


async def combine_streams(
    *streams: AsyncIterator[fp.PartialResponse],
) -> AsyncIterator[fp.PartialResponse]:
    """Combines a list of streams into one single response stream.

    Allows you to render multiple responses in parallel.

    """
    active_streams = {id(stream): stream for stream in streams}
    responses: dict[int, list[str]] = defaultdict(list)

    async def _advance_stream(
        stream_id: int, gen: AsyncIterator[fp.PartialResponse]
    ) -> tuple[int, fp.PartialResponse | None]:
        try:
            return stream_id, await gen.__anext__()
        except StopAsyncIteration:
            return stream_id, None

    while active_streams:
        for coro in asyncio.as_completed(
            [
                _advance_stream(stream_id, gen)
                for stream_id, gen in active_streams.items()
            ]
        ):
            stream_id, msg = await coro
            if msg is None:
                del active_streams[stream_id]
                continue

            if isinstance(msg, fp.MetaResponse):
                continue
            elif msg.is_suggested_reply:
                yield msg
                continue
            elif msg.is_replace_response:
                responses[stream_id] = [msg.text]
            else:
                responses[stream_id].append(msg.text)

            text = "\n\n".join(
                "".join(chunks) for stream_id, chunks in responses.items()
            )
            yield fp.PartialResponse(text=text, is_replace_response=True)


def preprocess_message(message: fp.ProtocolMessage, bot: str) -> fp.ProtocolMessage:
    """Process bot responses to keep only the parts that come from the given bot."""
    if message.role == "bot":
        parts = re.split(r"\*\*([A-Za-z_\-\d]+)\*\* says:\n", message.content)
        for message_bot, text in zip(parts[1::2], parts[2::2]):
            if message_bot.casefold() == bot.casefold():
                return message.model_copy(update={"content": text})
        # If we can't find a message by this bot, just return the original message
        return message
    else:
        return message


def preprocess_query(request: fp.QueryRequest, bot: str) -> fp.QueryRequest:
    """Parses the two bot responses and keeps the one for the current bot."""
    new_query = request.model_copy(
        update={
            "query": [preprocess_message(message, bot) for message in request.query]
        }
    )
    return new_query


async def stream_request_wrapper(
    request: fp.QueryRequest, bot: str
) -> AsyncIterator[fp.PartialResponse]:
    """Wraps stream_request and labels the bot response with the bot name."""
    label = fp.PartialResponse(
        text=f"**{bot.title()}** says:\n", is_replace_response=True
    )
    yield label
    async for msg in fp.stream_request(
        preprocess_query(request, bot), bot, request.access_key
    ):
        if isinstance(msg, Exception):
            yield fp.PartialResponse(
                text=f"**{bot.title()}** ran into an error", is_replace_response=True
            )
            return
        elif msg.is_replace_response:
            yield label
        # Force replace response to False since we are already explicitly handling that case above.
        yield msg.model_copy(update={"is_replace_response": False})


class GPT35TurbovsClaudeBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        streams = [
            stream_request_wrapper(request, bot)
            for bot in ("GPT-3.5-Turbo", "Claude-3.5-Haiku")
        ]
        async for msg in combine_streams(*streams):
            yield msg

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies={"GPT-3.5-Turbo": 1, "Claude-3.5-Haiku": 1}
        )


REQUIREMENTS = ["fastapi-poe==0.0.48"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App("turbo-vs-claude-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = GPT35TurbovsClaudeBot()
    # see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
    # app = fp.make_app(bot, access_key=<YOUR_ACCESS_KEY>, bot_name=<YOUR_BOT_NAME>)
    app = fp.make_app(bot, allow_without_key=True)
    return app
