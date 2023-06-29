"""

Sample bot that returns interleaved results from multiple bots.

"""
from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from typing import AsyncIterable, AsyncIterator, Sequence

from fastapi_poe import PoeBot
from fastapi_poe.client import BotMessage, MetaMessage, stream_request
from fastapi_poe.types import ProtocolMessage, QueryRequest
from sse_starlette.sse import ServerSentEvent

COMPARE_REGEX = r"\s([A-Za-z_\-\d]+)\s+vs\.?\s+([A-Za-z_\-\d]+)\s*$"


async def advance_stream(
    label: str, gen: AsyncIterator[BotMessage]
) -> tuple[str, BotMessage | Exception | None]:
    try:
        return label, await gen.__anext__()
    except StopAsyncIteration:
        return label, None
    except Exception as e:
        return label, e


async def combine_streams(
    streams: Sequence[tuple[str, AsyncIterator[BotMessage]]]
) -> AsyncIterator[tuple[str, BotMessage | Exception]]:
    active_streams = dict(streams)
    while active_streams:
        for coro in asyncio.as_completed(
            [advance_stream(label, gen) for label, gen in active_streams.items()]
        ):
            label, msg = await coro
            if msg is None:
                del active_streams[label]
            else:
                if isinstance(msg, Exception):
                    del active_streams[label]
                yield label, msg


def get_bots_to_compare(messages: Sequence[ProtocolMessage]) -> tuple[str, str]:
    for message in reversed(messages):
        if message.role != "user":
            continue
        match = re.search(COMPARE_REGEX, message.content)
        if match is not None:
            return match.groups()
    return ("sage", "claude-instant")


def preprocess_message(message: ProtocolMessage, bot: str) -> ProtocolMessage:
    """Preprocess the conversation history.

    For user messages, remove "x vs. y" from the end of the message.

    For bot messages, try to keep only the parts of the message that come from
    the bot we're querying.
    """
    if message.role == "user":
        new_content = re.sub(COMPARE_REGEX, "", message.content)
        return message.copy(update={"content": new_content})
    elif message.role == "bot":
        parts = re.split(r"\*\*([A-Za-z_\-\d]+)\*\* says:\n", message.content)
        for message_bot, text in zip(parts[1::2], parts[2::2]):
            if message_bot.casefold() == bot.casefold():
                return message.copy(update={"content": text})
        # If we can't find a message by this bot, just return the original message
        return message
    else:
        return message


def preprocess_query(query: QueryRequest, bot: str) -> QueryRequest:
    new_query = query.copy(
        update={"query": [preprocess_message(message, bot) for message in query.query]}
    )
    return new_query


class BattleBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        bots = get_bots_to_compare(query.query)
        streams = [
            (bot, stream_request(preprocess_query(query, bot), bot, query.api_key))
            for bot in bots
        ]
        label_to_responses: dict[str, list[str]] = defaultdict(list)
        async for label, msg in combine_streams(streams):
            if isinstance(msg, MetaMessage):
                continue
            elif isinstance(msg, Exception):
                label_to_responses[label] = [f"{label} ran into an error"]
            elif msg.is_suggested_reply:
                yield self.suggested_reply_event(msg.text)
                continue
            elif msg.is_replace_response:
                label_to_responses[label] = [msg.text]
            else:
                label_to_responses[label].append(msg.text)
            text = "\n\n".join(
                f"**{label.title()}** says:\n{''.join(chunks)}"
                for label, chunks in label_to_responses.items()
            )
            yield self.replace_response_event(text)
