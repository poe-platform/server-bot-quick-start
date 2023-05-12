"""

Demo bot: catbot.

"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterable

from sse_starlette.sse import ServerSentEvent

from fastapi_poe import PoeBot, run
from fastapi_poe.types import (
    ContentType,
    QueryRequest,
    ReportFeedbackRequest,
    SettingsRequest,
    SettingsResponse,
)

SETTINGS = SettingsResponse(
    context_clear_window_secs=60 * 60, allow_user_context_clear=True
)


class CatBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        """Return an async iterator of events to send to the user."""
        last_message = query.query[-1].content.lower()
        response_content_type: ContentType = (
            "text/plain" if "plain" in last_message else "text/markdown"
        )
        yield self.meta_event(
            content_type=response_content_type,
            linkify=True,
            refetch_settings=False,
            suggested_replies="dog" not in last_message,
        )
        if "markdown" in last_message:
            yield self.text_event("# Heading 1\n\n")
            yield self.text_event("*Bold text* ")
            yield self.text_event("**More bold text**\n")
            yield self.text_event("\n")
            yield self.text_event("A list:\n")
            yield self.text_event("- Item 1\n")
            yield self.text_event("- Item 2\n")
            yield self.text_event("- An item with [a link](https://poe.com)\n")
            yield self.text_event("\n")
            yield self.text_event("A table:\n\n")
            yield self.text_event("| animal | cuteness |\n")
            yield self.text_event("|--------|----------|\n")
            yield self.text_event("| cat    | 10       |\n")
            yield self.text_event("| dog    | 1        |\n")
            yield self.text_event("\n")
        if "cardboard" in last_message:
            yield self.text_event("crunch ")
            yield self.text_event("crunch")
        elif (
            "kitchen" in last_message
            or "meal" in last_message
            or "food" in last_message
        ):
            yield self.text_event("meow ")
            yield self.text_event("meow")
            yield self.suggested_reply_event("feed the cat")
        elif "stranger" in last_message:
            for _ in range(10):
                yield self.text_event("peek ")
                await asyncio.sleep(1)
        elif "square" in last_message:
            yield self.error_event("Square snacks are not tasty.")
        elif "cube" in last_message:
            yield self.error_event(
                "Cube snacks are even less tasty.", allow_retry=False
            )
        elif "count" in last_message:
            for i in range(1, 11):
                yield self.replace_response_event(str(i))
                if "quickly" not in last_message:
                    await asyncio.sleep(1)
        # These messages make the cat do something that's not allowed by the protocol
        elif "scratch" in last_message:
            yield ServerSentEvent(event="purr", data=json.dumps({"text": "purr"}))
        elif "toy" in last_message:
            for _ in range(1010):
                yield self.text_event("hit ")
        elif "bed" in last_message:
            yield self.text_event("z" * 10_010)
        else:
            yield self.text_event("zzz")

    async def on_feedback(self, feedback: ReportFeedbackRequest) -> None:
        """Called when we receive user feedback such as likes."""
        print(
            f"User {feedback.user_id} gave feedback on {feedback.conversation_id}"
            f"message {feedback.message_id}: {feedback.feedback_type}"
        )

    async def get_settings(self, settings: SettingsRequest) -> SettingsResponse:
        """Return the settings for this bot."""
        return SETTINGS


if __name__ == "__main__":
    run(CatBot())
