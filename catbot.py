"""

Demo bot: catbot.

This bot uses all options provided by the Poe protocol. You can use it to get examples
of all the protocol has to offer.

"""

from __future__ import annotations

import asyncio
from typing import AsyncIterable

import fastapi_poe as fp
from modal import App, Image, asgi_app, exit


class CatBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        """Return an async iterator of events to send to the user."""
        last_message = request.query[-1].content.lower()
        response_content_type = (
            "text/plain" if "plain" in last_message else "text/markdown"
        )
        yield fp.MetaResponse(
            text="",
            content_type=response_content_type,
            linkify=True,
            refetch_settings=False,
            suggested_replies="dog" not in last_message,
        )
        if "markdown" in last_message:
            yield fp.PartialResponse(text="# Heading 1\n\n")
            yield fp.PartialResponse(text="*Bold text* ")
            yield fp.PartialResponse(text="**More bold text**\n")
            yield fp.PartialResponse(text="\n")
            yield fp.PartialResponse(text="A list:\n")
            yield fp.PartialResponse(text="- Item 1\n")
            yield fp.PartialResponse(text="- Item 2\n")
            yield fp.PartialResponse(text="- An item with [a link](https://poe.com)\n")
            yield fp.PartialResponse(text="\n")
            yield fp.PartialResponse(text="A table:\n\n")
            yield fp.PartialResponse(text="| animal | cuteness |\n")
            yield fp.PartialResponse(text="|--------|----------|\n")
            yield fp.PartialResponse(text="| cat    | 10       |\n")
            yield fp.PartialResponse(text="| dog    | 1        |\n")
            yield fp.PartialResponse(text="\n")
        if "cardboard" in last_message:
            yield fp.PartialResponse(text="crunch ")
            yield fp.PartialResponse(text="crunch")
        elif (
            "kitchen" in last_message
            or "meal" in last_message
            or "food" in last_message
        ):
            yield fp.PartialResponse(text="meow ")
            yield fp.PartialResponse(text="meow")
            yield fp.PartialResponse(text="feed the cat", is_suggested_reply=True)
        elif "stranger" in last_message:
            for _ in range(10):
                yield fp.PartialResponse(text="peek ")
                await asyncio.sleep(1)
        elif "square" in last_message:
            yield fp.ErrorResponse(text="Square snacks are not tasty.")
        elif "cube" in last_message:
            yield fp.ErrorResponse(
                text="Cube snacks are even less tasty.", allow_retry=False
            )
        elif "count" in last_message:
            for i in range(1, 11):
                yield fp.PartialResponse(text=str(i), is_replace_response=True)
                if "quickly" not in last_message:
                    await asyncio.sleep(1)
        else:
            yield fp.PartialResponse(text="zzz")

    async def on_feedback(self, feedback_request: fp.ReportFeedbackRequest) -> None:
        """Called when we receive user feedback such as likes."""
        print(
            f"User {feedback_request.user_id} gave feedback on {feedback_request.conversation_id}"
            f"message {feedback_request.message_id}: {feedback_request.feedback_type}"
        )

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        """Return the settings for this bot."""
        return fp.SettingsResponse(
            allow_user_context_clear=True, allow_attachments=True
        )


REQUIREMENTS = ["fastapi-poe==0.0.47"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App(name="catbot-poe", image=image)


@app.cls(image=image)
class Model:
    # See https://creator.poe.com/docs/quick-start#integrating-with-poe to find these values.
    access_key: str | None = None  # REPLACE WITH YOUR ACCESS KEY
    bot_name: str | None = None  # REPLACE WITH YOUR BOT NAME

    @exit()
    def sync_settings(self):
        """Syncs bot settings on server shutdown."""
        if self.bot_name and self.access_key:
            try:
                fp.sync_bot_settings(self.bot_name, self.access_key)
            except Exception:
                print("\n*********** Warning ***********")
                print(
                    "Bot settings sync failed. For more information, see: https://creator.poe.com/docs/server-bots-functional-guides#updating-bot-settings"
                )
                print("\n*********** Warning ***********")

    @asgi_app()
    def fastapi_app(self):
        bot = CatBot()
        if not self.access_key:
            print(
                "Warning: Running without an access key. Please remember to set it before production."
            )
            app = fp.make_app(bot, allow_without_key=True)
        else:
            app = fp.make_app(bot, access_key=self.access_key)
        return app


@app.local_entrypoint()
def main():
    Model().run.remote()
