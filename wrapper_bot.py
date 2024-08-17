"""

Sample bot that wraps OpenAI async API.

"""

from __future__ import annotations

import os
from typing import AsyncIterable

import fastapi_poe as fp
from modal import App, Image, asgi_app, exit
from openai import AsyncOpenAI

client = AsyncOpenAI()


async def stream_chat_completion(request: fp.QueryRequest):
    messages = []
    # this is a demo bot, the messages and message length will be truncated
    for query in request.query[-5:]:
        if query.role == "system":
            messages.append({"role": "system", "content": query.content[:50]})
        elif query.role == "bot":
            messages.append({"role": "assistant", "content": query.content[:50]})
        elif query.role == "user":
            messages.append({"role": "user", "content": query.content[:50]})
        else:
            raise

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=1.0,
        stream=True,
        max_tokens=50,
    )

    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield fp.PartialResponse(text=chunk.choices[0].delta.content)


class WrapperBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        async for msg in stream_chat_completion(request):
            yield msg


REQUIREMENTS = ["fastapi-poe==0.0.47", "openai"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .env(
        {
            "POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"],
            "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
        }
    )
)
app = App(name="wrapper-bot-poe", image=image)


@app.cls(image=image)
class Model:
    # See https://creator.poe.com/docs/quick-start#integrating-with-poe to find these values.
    access_key: str | None = os.environ["POE_ACCESS_KEY"]
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
        bot = WrapperBot()
        app = fp.make_app(bot, access_key=self.access_key)
        return app


@app.local_entrypoint()
def main():
    Model().run.remote()
