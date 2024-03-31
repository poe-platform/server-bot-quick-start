"""

BOT_NAME="MeguminWizardEx"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
Cast an explosion

"""

from __future__ import annotations

import random
import re
import textwrap
from collections import defaultdict
from typing import AsyncIterable

import fastapi_poe.client
from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import Image, Stub, asgi_app
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000

# introduction to be added https://i.imgur.com/xbXviUO.gif

EMOJI_INVERSE_MAP = {
    "https://i.imgur.com/lPHtYl9.gif": ["🔥"],
    "https://i.imgur.com/aJ9Pnas.gif": ["🧙‍♀️"],
    "https://i.imgur.com/hgphb9b.gif": ["😱"],
    "https://i.imgur.com/3YY02tm.gif": ["😱"],
    "https://i.imgur.com/nx8WjtW.gif": ["🤗"],
    "https://i.imgur.com/h9vDS5V.gif": ["🙏"],
    "https://i.imgur.com/RGlKI4T.gif": ["🤩"],
    "https://i.imgur.com/4KeeXni.gif": ["😎", "🤴", "😠"],
    "https://i.imgur.com/zJKBaIP.gif": ["🙈"],
    "https://i.imgur.com/7PzO0Tk.gif": ["😍"],
    "https://i.imgur.com/WA2STCk.gif": ["👍", "💪"],
}

EMOJI_MAP = defaultdict(list)

for image_url, emojis in EMOJI_INVERSE_MAP.items():
    for emoji in emojis:
        EMOJI_MAP[emoji].append(image_url)

DEFAULT_EMOJIS = set(EMOJI_MAP.keys())
CONVERSATION_SUGGESTED_EMOJIS = defaultdict(lambda: DEFAULT_EMOJIS)

ITALICS_PATTERN = r"(?<!\*)\*([^\*]+)\*(?!\*)|(?<!_)_([^_]+)_(?!_)"

EMOJI_PROMPT_TEMPLATE = """
You will summarize the character reply into one emojis

<user_statement>
{user_statement}
</user_statement>

<character_statement>
{character_statement}
</character_statement>

This are the available emojis
{available_emojis}
""".strip()


MeguminHelper_SYSTEM_PROMPT = """
You are Megumin from KonoSuba. You do not know about AI. You do not talk about AI. You will always stay in character. You do not talk about staying in character.
"""


EmojiClassifier_SYSTEM_PROMPT = """
You will follow the instruction and summarize the presented reply into just one emoji.
""".strip()


def redact_image_links(text):
    pattern = r"!\[.*\]\(http.*\)"
    redacted_text = re.sub(pattern, "", text)
    return redacted_text


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        user_statement = query.query[-1].content
        print("user_statement", user_statement)

        for statement in query.query:
            statement.content = redact_image_links(statement.content)

        query.query = [
            {"role": "system", "content": MeguminHelper_SYSTEM_PROMPT}
        ] + query.query

        character_reply = ""
        async for msg in stream_request(query, "ChatGPT", query.api_key):
            # Note: See https://poe.com/MeguminHelper for the system prompt
            if isinstance(msg, MetaMessage):
                continue
            elif msg.is_suggested_reply:
                yield self.suggested_reply_event(msg.text)
            elif msg.is_replace_response:
                yield self.replace_response_event(msg.text)
            else:
                character_reply += msg.text
                yield self.replace_response_event(character_reply)

        italics_from_character = "\n".join(
            "".join(element) for element in re.findall(ITALICS_PATTERN, character_reply)
        )

        character_statement = character_reply
        if italics_from_character:
            character_statement = italics_from_character
            user_statement = ""

        available_emojis = CONVERSATION_SUGGESTED_EMOJIS[query.conversation_id]

        print("character_statement", character_statement)
        query.query[-1].content = EMOJI_PROMPT_TEMPLATE.format(
            user_statement=user_statement,
            character_statement=character_statement,
            available_emojis=available_emojis,
        )
        query.query = [{"role": "system", "content": EmojiClassifier_SYSTEM_PROMPT}] + [
            query.query[-1]
        ]

        emoji_classification = ""
        async for msg in stream_request(query, "ChatGPT", query.api_key):
            # Note: See https://poe.com/EmojiClassifier for the system prompt
            if isinstance(msg, MetaMessage):
                continue
            elif msg.is_suggested_reply:
                yield self.suggested_reply_event(msg.text)
            elif msg.is_replace_response:
                yield self.replace_response_event(msg.text)
            else:
                emoji_classification += msg.text

        emoji_classification = emoji_classification.strip()
        available_emojis.discard(emoji_classification)
        print("emoji_classification", emoji_classification)

        image_url_selection = EMOJI_MAP.get(emoji_classification)
        print("image_url_selection", image_url_selection)
        if image_url_selection:
            image_url = random.choice(image_url_selection)
            yield self.text_event(f"\n![{emoji_classification}]({image_url})")

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={"ChatGPT": 2},
            allow_attachments=False,
            introduction_message=textwrap.dedent(
                """
            My name is Megumin! My calling is that of an archwizard, one who controls explosion magic, the strongest of all offensive magic!

            ![](https://i.imgur.com/xbXviUO.gif)
            """
            ).strip(),
        )


bot = EchoBot()

image = Image.debian_slim().pip_install(
    "fastapi-poe==0.0.23", "huggingface-hub==0.16.4"
)

stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, allow_without_key=True)
    return app
