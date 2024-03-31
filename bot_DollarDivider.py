"""

BOT_NAME="DollarDivider"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
Upload a receipt

"""

from __future__ import annotations

import os
import re
import time
from typing import AsyncIterable, Union

import fastapi_poe.client
import tiktoken
from fastapi_poe import PoeBot, make_app
from fastapi_poe.types import (
    PartialResponse,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
from modal import Dict, Image, Stub, asgi_app
from openai import OpenAI
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000

DAY_IN_SECS = 24 * 60 * 60

# for non-subscribers, the message limit is defined in the bot settings
SUBSCRIBER_DAILY_TOKEN_LIMIT = 200_000

encoding = tiktoken.encoding_for_model("gpt-4-1106-preview")


stub = Stub("poe-bot-quickstart")
stub.my_dict = Dict.new()

user_allowlist = {}


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


def split_markdown_text_images(
    markdown_text,
) -> list[dict[str, Union(str, dict[str, str])]]:
    # This regex will match Markdown image syntax
    image_regex = r'!\[([^\]]*)\]\(([^\s]+)(?:\s+"([^"]+)")?\)'

    # Split the text based on the regex
    parts = re.split(image_regex, markdown_text)

    # Interleave text and images
    interleaved = []
    i = 0
    while i < len(parts):
        text = parts[i]
        if text:
            interleaved.append({"type": "text", "text": text})
        if i + 3 < len(parts):
            alt_text, image_url, optional_title = parts[i + 1 : i + 4]
            image_info = {
                "type": "image_url",
                # 'alt_text': alt_text,
                "image_url": {"url": image_url},
                # 'title': optional_title or ''
            }
            interleaved.append(image_info)
        i += 4

    return interleaved


SYSTEM_PROMPT = """
You will split the bill given the receipt.

Follow these assumptions, unless specified in the conversation otherwise
- The taxes and tips are split proportionally with the menu price.
- Each person only orders one item (even if we see multiple of the same item being ordered).

Reply in the following format

Attribute the items to the people. If the names are not specified, use Person 1, Person 2, etc.
Present the table in the following format.

| Menu Item | Menu Price | Person |
| --------- | ---------- | ------ |
| MENU_ITEM | MENU_PRICE | PERSON |
| MENU_ITEM | MENU_PRICE | PERSON, PERSON |

Do math to check that the sum of menu prices adds up to the menu subtotal. Restart from scratch if it does not add up.

Calulate the percentage of additional charges by dividing the total price (after tax, tips, etc) with the menu subtotal.

Enumerate for each person to calculate the amount payable. Restart from scratch if it does not add up.

Do math to check that the sum of amount payable adds up to the total price (which includes tax, tips, etc).

Present the table in the following format. Do not do math in the table, do it before presenting the table.

| Person | Total Menu Price | Amount Payable | Payment |
| ------ | ---------------- | -------------- | ------- |
| PERSON | TOTAL_MENU_PRICE | AMOUNT_PAYABLE | [Venmo](https://venmo.com/?txn=charge&amount=AMOUNT_PAYABLE&note=NOTE) |
| PERSON | TOTAL_MENU_PRICE | AMOUNT_PAYABLE | [Venmo](https://venmo.com/?txn=charge&amount=AMOUNT_PAYABLE&note=NOTE) |

Replace NOTE with the following format (STORE_NAME | MENU_ITEM MENU_PRICE_SHARE | via DollarDivider on Poe).
- Escape all non-alphanumeric characters with URL encoding
- Escape whitespace with %E2%80%84 (NEVER use %20)
- Example: Masa%E2%80%84Sushi%E2%80%84%7C%E2%80%84California%E2%80%84Roll%E2%80%84$12.34%E2%80%84%7C%E2%80%84via%E2%80%84DollarDivider%E2%80%84on%E2%80%84Poe

REPEAT: NEVER USE %20 for URL encoding. NEVER EVER USE %20.
""".strip()


SYSTEM_MESSAGE = {"role": "system", "content": SYSTEM_PROMPT}


class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[ServerSentEvent]:
        print(request.user_id)
        print(request.query[-1].content)

        token_count = sum(
            len(encoding.encode(query.content)) for query in request.query
        )

        # randval = random.randint(0, int(token_count**0.5))
        # print("randval", randval)
        # if request.query[-1].content.startswith("[{'role': '") and randval > 0:
        #     yield PartialResponse(text="")
        #     time.sleep(random.randint(0, max(10, min(100, token_count))))
        #     return

        # check message limit
        dict_key = f"gpt4-mirror-token-limit-{request.user_id}"

        current_time = time.time()

        if dict_key not in stub.my_dict:
            stub.my_dict[dict_key] = []

        calls = stub.my_dict[dict_key]

        while calls and calls[0][0] <= current_time - DAY_IN_SECS:
            del calls[0]

        # if len(calls) == 0 and token_count >= 1000:
        #     print(request.user_id, len(calls), token_count)
        #     yield PartialResponse(
        #         text="Please subscribe to Poe to send longer messages.\n\nIf you have subscribed, please start a new chat, send a short message, and then retry."
        #     )
        #     return

        if (
            sum(weight for _, weight in calls) >= SUBSCRIBER_DAILY_TOKEN_LIMIT
            and request.user_id not in user_allowlist
        ):
            print(request.user_id, len(calls))
            time_remaining = calls[0][0] + DAY_IN_SECS - current_time
            yield PartialResponse(text=prettify_time_string(time_remaining))
            return

        calls.append((current_time, token_count))
        stub.my_dict[dict_key] = calls
        print(calls)

        client = OpenAI()

        openai_messages = [SYSTEM_MESSAGE]
        openai_messages_no_image = [SYSTEM_MESSAGE]
        conversation_has_image = False
        for query in request.query:
            if query.role == "bot":
                openai_messages_no_image.append(
                    {"role": "assistant", "content": query.content}
                )
                openai_messages.append(
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": query.content}],
                    }
                )
            if query.role == "user":
                openai_messages_no_image.append(
                    {"role": query.role, "content": query.content}
                )
                openai_messages.append(
                    {
                        "role": query.role,
                        "content": split_markdown_text_images(query.content),
                    }
                )
                for attachment in query.attachments:
                    print(attachment.content_type)
                    if attachment.content_type.startswith("image/"):
                        openai_messages[-1]["content"].append(
                            {"type": "image_url", "image_url": {"url": attachment.url}}
                        )
                        conversation_has_image = True
                        print(attachment.url)
                        calls = stub.my_dict[dict_key]
                        calls.append((current_time, 1000))
                        stub.my_dict[dict_key] = calls
                    else:
                        yield PartialResponse(
                            text=f"Attaching {attachment.name} is not supported.\n\n"
                        )

            if query.role == "system":
                openai_messages_no_image.append(
                    {"role": query.role, "content": query.content}
                )
                openai_messages.append(
                    {
                        "role": query.role,
                        "content": [{"type": "text", "text": query.content}],
                    }
                )

        if conversation_has_image:
            stream = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=openai_messages,
                stream=True,
                max_tokens=4096,
                # logit bias is not working
            )
        else:
            stream = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=openai_messages_no_image,
                stream=True,
                max_tokens=4096,
            )

        yield PartialResponse(text="", is_replace_response=True)

        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield PartialResponse(text=chunk.choices[0].delta.content)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={"GPT-4": 1},
            allow_attachments=True,
            introduction_message="Please upload your receipt.",
        )


bot = EchoBot()

image = (
    Image.debian_slim()
    .pip_install("fastapi-poe==0.0.32", "openai==1.1.0", "tiktoken")
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
