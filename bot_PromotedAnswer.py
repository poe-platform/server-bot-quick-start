"""

BOT_NAME="PromotedAnswer"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
neverssl.com

"""

from __future__ import annotations

from typing import AsyncIterable
from urllib.parse import urlparse, urlunparse

import fastapi_poe.client
import requests
from bs4 import BeautifulSoup
from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import Image, Stub, asgi_app
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000

PROMPT_TEMPLATE = """
You are given the the content from the site {url}.
The owner of the site wants to advertise on Quora, a question-and-answer site.

<content>
{content}
</content>

Write a meaningful question
- Do not mention the product in the question.

Write an authentic answer
- Do not promote the product early.
- Break down the answer into smaller paragraphs.
- At the end of the answer, organically and naturally promote the product.
- When the product is mentioned, use markdown to make a hyperlink.

Reply in the following format in markdown. Do not add words.

<question>
---
<answer>""".strip()

conversation_cache = set()


def resolve_url_scheme(url):
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        parsed_url = parsed_url._replace(scheme="https")
    resolved_url = urlunparse(parsed_url)
    resolved_url = resolved_url.replace(":///", "://")
    return resolved_url


def insert_newlines(element):
    block_level_elements = [
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "blockquote",
        "pre",
        "figure",
    ]

    for tag in element.find_all(block_level_elements):
        if tag.get_text(strip=True):
            tag.insert_before("\n")
            tag.insert_after("\n")


def extract_readable_text(url):
    try:
        response = requests.get(url)
    except requests.exceptions.InvalidURL:
        print(f"URL is invalid: {url}")
        return None
    except Exception:
        print(f"Unable to load URL: {url}")
        return None

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()

        insert_newlines(soup)

        readable_text = soup.get_text()

        # Clean up extra whitespaces without collapsing newlines
        readable_text = "\n".join(
            " ".join(line.split()) for line in readable_text.split("\n")
        )

        return readable_text

    else:
        print(f"Request failed with status code {response.status_code}")
        return None


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        print("user_statement", query.query[-1].content)

        if query.conversation_id not in conversation_cache:
            url = query.query[-1].content.strip()
            url = resolve_url_scheme(url)
            yield self.replace_response_event(f"Attempting to load [{url}]({url}) ...")
            content = extract_readable_text(url)
            if content is None:
                yield self.replace_response_event(
                    "Please submit an URL that you want to create a promoted answer for."
                )
                return
            content = content[:5000]  # TODO: use Tiktoken

            # replace last message with the prompt
            query.query[-1].content = PROMPT_TEMPLATE.format(content=content, url=url)
            conversation_cache.add(query.conversation_id)
            yield self.replace_response_event("")

        current_message = ""

        async for msg in stream_request(query, "AnswerPromoted", query.api_key):
            # Note: See https://poe.com/AnswerPromoted for the prompt
            if isinstance(msg, MetaMessage):
                continue
            elif msg.is_suggested_reply:
                yield self.suggested_reply_event(msg.text)
            elif msg.is_replace_response:
                yield self.replace_response_event(msg.text)
            else:
                current_message += msg.text
                yield self.replace_response_event(current_message)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={"AnswerPromoted": 1},
            allow_attachments=False,
            introduction_message="Please start this conversation with the URL of the website you want to promote.",
        )


bot = EchoBot()

image = Image.debian_slim().pip_install(
    "fastapi-poe==0.0.23", "requests==2.31.0", "beautifulsoup4==4.10.0"
)

stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, allow_without_key=True)
    return app
