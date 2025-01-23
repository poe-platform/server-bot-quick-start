"""

Sample bot that wraps OpenAI async API.

"""

from __future__ import annotations

import os
from typing import AsyncIterable

import fastapi_poe as fp
from modal import App, Image, asgi_app
from openai import AsyncOpenAI

# TODO: set your bot access key, and openai api key, and bot name for this bot to work
# see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
bot_access_key = os.getenv("POE_ACCESS_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
bot_name = ""

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


REQUIREMENTS = ["fastapi-poe", "openai"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .env({"POE_ACCESS_KEY": bot_access_key, "OPENAI_API_KEY": openai_api_key})
)
app = App("wrapper-bot-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = WrapperBot()
    app = fp.make_app(
        bot,
        access_key=bot_access_key,
        bot_name=bot_name,
        allow_without_key=not (bot_access_key and bot_name),
    )
    return app
