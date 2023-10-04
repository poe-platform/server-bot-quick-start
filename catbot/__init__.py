"""

Demo bot: catbot.

This bot uses all options provided by the Poe protocol. You can use it to get examples
of all the protocol has to offer.

"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterable

from fastapi_poe import PoeBot
from fastapi_poe.types import (
    ContentType,
    ErrorResponse,
    MetaResponse,
    PartialResponse,
    QueryRequest,
    ReportFeedbackRequest,
    SettingsRequest,
    SettingsResponse,
)
from sse_starlette.sse import ServerSentEvent

SETTINGS = SettingsResponse(allow_user_context_clear=True, allow_attachments=True)


class CatBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse | ServerSentEvent]:
        """Return an async iterator of events to send to the user."""
        last_message = request.query[-1].content.lower()
        response_content_type: ContentType = (
            "text/plain" if "plain" in last_message else "text/markdown"
        )
        yield MetaResponse(
            text="",
            content_type=response_content_type,
            linkify=True,
            refetch_settings=False,
            suggested_replies="dog" not in last_message,
        )
        if "markdown" in last_message:
            yield PartialResponse(text="# Heading 1\n\n")
            yield PartialResponse(text="*Bold text* ")
            yield PartialResponse(text="**More bold text**\n")
            yield PartialResponse(text="\n")
            yield PartialResponse(text="A list:\n")
            yield PartialResponse(text="- Item 1\n")
            yield PartialResponse(text="- Item 2\n")
            yield PartialResponse(text="- An item with [a link](https://poe.com)\n")
            yield PartialResponse(text="\n")
            yield PartialResponse(text="A table:\n\n")
            yield PartialResponse(text="| animal | cuteness |\n")
            yield PartialResponse(text="|--------|----------|\n")
            yield PartialResponse(text="| cat    | 10       |\n")
            yield PartialResponse(text="| dog    | 1        |\n")
            yield PartialResponse(text="\n")
        if "cardboard" in last_message:
            yield PartialResponse(text="crunch ")
            yield PartialResponse(text="crunch")
        elif (
            "kitchen" in last_message
            or "meal" in last_message
            or "food" in last_message
        ):
            yield PartialResponse(text="meow ")
            yield PartialResponse(text="meow")
            yield PartialResponse(text="feed the cat", is_suggested_reply=True)
        elif "stranger" in last_message:
            for _ in range(10):
                yield PartialResponse(text="peek ")
                await asyncio.sleep(1)
        elif "square" in last_message:
            yield ErrorResponse(text="Square snacks are not tasty.")
        elif "cube" in last_message:
            yield ErrorResponse(
                text="Cube snacks are even less tasty.", allow_retry=False
            )
        elif "count" in last_message:
            for i in range(1, 11):
                yield PartialResponse(text=str(i), is_replace_response=True)
                if "quickly" not in last_message:
                    await asyncio.sleep(1)
        # These messages make the cat do something that's not allowed by the protocol
        elif "scratch" in last_message:
            yield ServerSentEvent(event="purr", data=json.dumps({"text": "purr"}))
        elif "toy" in last_message:
            for _ in range(1010):
                yield PartialResponse(text="hit ")
        elif "bed" in last_message:
            yield PartialResponse(text="z" * 10_010)
        else:
            yield PartialResponse(text="zzz")

    async def on_feedback(self, feedback_request: ReportFeedbackRequest) -> None:
        """Called when we receive user feedback such as likes."""
        print(
            f"User {feedback_request.user_id} gave feedback on {feedback_request.conversation_id}"
            f"message {feedback_request.message_id}: {feedback_request.feedback_type}"
        )

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        """Return the settings for this bot."""
        return SETTINGS
