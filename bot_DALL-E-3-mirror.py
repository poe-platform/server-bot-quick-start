"""

BOT_NAME="DALL-E-3-mirror"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
ChatGPT

"""

from __future__ import annotations

import json
import os
import re
import time
from copy import deepcopy
from typing import AsyncIterable

import fastapi_poe.client
from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import stream_request
from fastapi_poe.types import (
    PartialResponse,
    ProtocolMessage,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
from modal import Dict, Image, Stub, asgi_app
from openai import BadRequestError, OpenAI
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000

DAY_IN_SECS = 24 * 60 * 60
MINUTE_IN_SECS = 60

# for non-subscribers, the message limit is defined in the bot settings
SUBSCRIBER_DAILY_MESSAGE_LIMIT = 100
GLOBAL_MINUTELY_MESSAGE_LIMIT = 5
GLOBAL_RATE_LIMIT_DICT_KEY = "dalle3-mirror-limit-"

stub = Stub("poe-bot-quickstart")
stub.my_dict = Dict.new()


SUGGESTED_REPLIES_REGEX = re.compile(r"<a>(.+?)</a>", re.DOTALL)

user_allowlist = {"u-000000xy92lqvf0s6x4s2mn6so7bu4ye"}

USER_FOLLOWUP_PROMPT = """
Read my conversation.

Please write a description of the image that I intend to generate.

The description should only be one paragraph.

Put the description inside ```prompt
"""

SUGGESTED_REPLIES_PROMPT = """
Read my conversation.

Suggest three ways I would request for changes to the image.

Each change request should be concise, and only describes what should be different.

Begin each suggestion with <a> and end each suggestion with </a>.
"""


def extract_suggested_replies(raw_output: str) -> list[str]:
    suggested_replies = [
        suggestion.strip() for suggestion in SUGGESTED_REPLIES_REGEX.findall(raw_output)
    ]
    return suggested_replies


def extract_prompt(reply) -> str:
    pattern = r"```prompt([\s\S]*?)```"
    matches = re.findall(pattern, reply)
    return ("\n\n".join(matches)).strip()


def prettify_time_string(second) -> str:
    second = int(second)
    hour, second = divmod(second, 60 * 60)
    minute, second = divmod(second, 60)

    string = "You can send the next message in"
    if hour == 1:
        string += f" {hour} hour"
    elif hour > 1:
        string += f" {hour} hours"

    if minute == 1:
        string += f" {minute} minute"
    elif minute > 1:
        string += f" {minute} minutes"

    if second == 1:
        string += f" {second} second"
    elif second > 1:
        string += f" {second} seconds"

    return string


class DALLE3Bot(PoeBot):
    image_quality = "standard"

    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[ServerSentEvent]:
        original_request = deepcopy(request)
        print(request.user_id)
        print(request.query[-1].content)

        client = OpenAI()

        current_time = time.time()

        if GLOBAL_RATE_LIMIT_DICT_KEY not in stub.my_dict:
            stub.my_dict[GLOBAL_RATE_LIMIT_DICT_KEY] = []

        calls = stub.my_dict[GLOBAL_RATE_LIMIT_DICT_KEY]

        while calls and calls[0] <= current_time - MINUTE_IN_SECS:
            del calls[0]

        if len(calls) >= GLOBAL_MINUTELY_MESSAGE_LIMIT:
            print(request.user_id, len(calls))
            yield PartialResponse(
                text="The bot is experiencing high traffic, please try again later."
            )
            return

        calls.append(current_time)
        stub.my_dict[GLOBAL_RATE_LIMIT_DICT_KEY] = calls

        # check message limit
        dict_key = f"dalle3-mirror-limit-{request.user_id}"

        current_time = time.time()

        if dict_key not in stub.my_dict:
            stub.my_dict[dict_key] = []

        calls = stub.my_dict[dict_key]

        while calls and calls[0] <= current_time - DAY_IN_SECS:
            del calls[0]

        if (
            len(calls) >= SUBSCRIBER_DAILY_MESSAGE_LIMIT
            and request.user_id not in user_allowlist
        ):
            print(request.user_id, len(calls))
            time_remaining = calls[0] + DAY_IN_SECS - current_time
            yield PartialResponse(text=prettify_time_string(time_remaining))
            return

        calls.append(current_time)
        stub.my_dict[dict_key] = calls

        bot_statement = ""

        # construct instruction if this is a multiline prompt
        if len(request.query) > 2:
            # this is a multi-turn conversation
            print("len(request)", len(request.query))
            message = ProtocolMessage(role="user", content=USER_FOLLOWUP_PROMPT)
            request.query.append(message)

            inferred_reply = ""
            async for msg in stream_request(request, "ChatGPT", request.api_key):
                inferred_reply += msg.text

            instruction = extract_prompt(inferred_reply)

            if not instruction:
                yield PartialResponse(text=inferred_reply)
                return

            bot_statement += instruction + "\n\n"
            yield PartialResponse(text=f"```instruction\n{instruction}\n```\n\n")
        else:
            instruction = request.query[-1].content

        print(instruction)
        print(stub.my_dict[dict_key])

        # generate image
        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=instruction,
                size="1024x1024",
                quality=self.image_quality,
                n=1,
            )
        except BadRequestError as error:
            error_message = json.loads(error.response.content.decode())["error"][
                "message"
            ]
            yield PartialResponse(text=error_message)
            calls = stub.my_dict[dict_key]
            calls.remove(current_time)
            stub.my_dict[dict_key] = calls
            return

        if response.data[0].revised_prompt:
            revised_prompt = response.data[0].revised_prompt
            image_url = response.data[0].url
            bot_statement += revised_prompt
            yield PartialResponse(text=f"```prompt\n{revised_prompt}\n```\n\n")

        print(image_url)

        yield PartialResponse(text=f"![image]({image_url})")

        # generate suggested replies
        request = deepcopy(original_request)
        message = ProtocolMessage(role="bot", content=bot_statement)
        request.query.append(message)
        message = ProtocolMessage(role="user", content=SUGGESTED_REPLIES_PROMPT)
        request.query.append(message)

        response_text = ""
        async for msg in stream_request(request, "ChatGPT", request.api_key):
            response_text += msg.text

        print(response_text)

        suggested_replies = extract_suggested_replies(response_text)

        for suggested_reply in suggested_replies[:3]:
            yield PartialResponse(text=suggested_reply, is_suggested_reply=True)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={"ChatGPT": 2, "DALL-E-3": 1},
            allow_attachments=False,
            introduction_message="What picture do you want to create with OpenAI DALL·E 3?",
        )


bot = DALLE3Bot()

image = (
    Image.debian_slim()
    .pip_install("fastapi-poe==0.0.23", "openai==1.1.0")
    .env(
        {
            "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
            "POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"],
        }
    )
)


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
