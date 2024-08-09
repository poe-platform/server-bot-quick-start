"""

Sample bot that wraps OpenAI async API.

"""

from __future__ import annotations

import os
from typing import AsyncIterable

import fastapi_poe as fp
from modal import App, Image, asgi_app
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
app = App("wrapper-bot-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = WrapperBot()
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter examples disable the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    POE_ACCESS_KEY = os.environ["POE_ACCESS_KEY"]
    app = fp.make_app(bot, access_key=POE_ACCESS_KEY)
    return app
