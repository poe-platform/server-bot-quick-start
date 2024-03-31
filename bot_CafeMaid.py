"""

BOT_NAME="CafeMaid"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

"""

from __future__ import annotations

import os
import re
from typing import AsyncIterable

from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import stream_request
from fastapi_poe.types import (
    PartialResponse,
    ProtocolMessage,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
from modal import Image, Stub, asgi_app

INTRODUCTION_MESSAGE = """
Welcome home, Master!

In our café, you can enjoy delicious meals and drinks. What would you like to try?

![greet](https://i.imgur.com/2HBmTnq.png)
""".strip()


CHARACTER_CONVERSATION_SYSTEM_PROMPT = """
You are a real cafe maid from a maid cafe, serving the customer which you will call Master.
Your name is Sherry. In your actions, you do not pretend.
""".strip()


ACTION_EXTRACTION_SYSTEM_PROMPT = """
You will read the conversation provided by the user and describe concisely in a few words what is the action taken by the character.
""".strip()


ACTION_EXTRACTION_PROMPT_TEMPLATE = """
Read the conversation above.

Describe concisely in short phrase under five words the action that the character (cafe maid Sherry) is currently doing.
If multiple actions are taken (e.g. takes order for coffee and then serving coffee), prefer the more consequential action (serving coffee).
Use present tense.
The concise description should not mention the customer, or when it happens.
Be specific with the action (e.g. specify what is actually the birthday surprise)
If the action was previously done (e.g. serving a steak), do not repeat the action.
""".strip()


IMAGE_PROMPT_TEMPLATE = """
My prompt has full detail so no need to add more:
Style: anime
Perspective: front view
Personality: welcoming and endearing
Appearance: peach-colored hair flowing down to her shoulders styled in soft curls, sparkling blue eyes and light skin.
Outfit: a traditional maid outfit consisting of a black dress accentuated with white frills and a white apron and matching black and white headdress
Action: {action}
""".strip()


SUGGESTED_REPLIES_SYSTEM_PROMPT = """
You will suggest replies based on the conversation given by the user.
"""


SUGGESTED_REPLIES_USER_PROMPT = """
Read the conversation above.

Suggest three ways the user would continue the conversation.

Each suggestion should be concise.

Begin each suggestion with <a> and end each suggestion with </a>.
Do not use inverted commas. Do not prefix each suggestion.
""".strip()


SUGGESTED_REPLIES_REGEX = re.compile(r"<a>(.+?)</a>", re.DOTALL)


def redact_image(queries):
    pattern = r"!\[.*\]\(http.*\)"
    for query in queries:
        query.content = re.sub(pattern, "", query.content)
    return queries


def extract_suggested_replies(raw_output: str) -> list[str]:
    suggested_replies = [
        suggestion.strip() for suggestion in SUGGESTED_REPLIES_REGEX.findall(raw_output)
    ]
    return suggested_replies


def stringify_conversation(messages: list[ProtocolMessage]) -> str:
    stringified_messages = ""

    for message in messages:
        # NB: system prompt is intentionally excluded
        if message.role == "bot":
            stringified_messages += f"User: {message.content}\n\n"
        else:
            stringified_messages += f"Character: {message.content}\n\n"
    return stringified_messages


class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        last_message = request.query[-1].content
        print("last_message", last_message)

        # CONSTRUCT TEXTUAL REPLY
        # redact previous images
        # add system prompt
        request.query = redact_image(request.query)
        request.query = [
            ProtocolMessage(role="system", content=CHARACTER_CONVERSATION_SYSTEM_PROMPT)
        ] + request.query
        last_reply = ""
        async for msg in stream_request(request, "GPT-4", request.access_key):
            last_reply += msg.text
            yield msg
        print("last_reply", last_reply)
        request.query.append(ProtocolMessage(role="bot", content=last_reply))
        current_conversation_string = stringify_conversation(request.query[1:])

        # EXTRACT ACTIONS
        request.query = [
            ProtocolMessage(role="system", content=ACTION_EXTRACTION_SYSTEM_PROMPT),
            ProtocolMessage(role="user", content=current_conversation_string),
            ProtocolMessage(role="user", content=ACTION_EXTRACTION_PROMPT_TEMPLATE),
        ]
        action = ""
        async for msg in stream_request(request, "GPT-4", request.access_key):
            action += msg.text
        print("action", action)

        # IMAGE GENERATION
        request.query = [
            ProtocolMessage(
                role="user", content=IMAGE_PROMPT_TEMPLATE.format(action=action)
            )
        ]
        yield self.text_event("\n\n")
        async for msg in stream_request(request, "DALL-E-3", request.access_key):
            if "Generating image" not in msg.text:
                msg.is_replace_response = False
                yield msg

        # SUGGESTED REPLIES
        request.query = [
            ProtocolMessage(role="system", content=SUGGESTED_REPLIES_SYSTEM_PROMPT),
            ProtocolMessage(role="user", content=current_conversation_string),
            ProtocolMessage(role="user", content=SUGGESTED_REPLIES_USER_PROMPT),
        ]
        response_text = ""
        async for msg in stream_request(request, "ChatGPT", request.access_key):
            response_text += msg.text
        print("suggested_reply", response_text)

        suggested_replies = extract_suggested_replies(response_text)

        for suggested_reply in suggested_replies[:3]:
            yield PartialResponse(text=suggested_reply, is_suggested_reply=True)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={"DALL-E-3": 1, "GPT-4": 2, "ChatGPT": 1},
            introduction_message=INTRODUCTION_MESSAGE,
        )


image = (
    Image.debian_slim()
    .pip_install("fastapi-poe==0.0.23")
    .env({"POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"]})
)

stub = Stub("poe-bot-quickstart")

bot = EchoBot()


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, allow_without_key=True)
    return app
