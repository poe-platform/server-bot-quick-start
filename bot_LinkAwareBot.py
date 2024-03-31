"""

BOT_NAME="LinkAwareBot"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
What is the difference between https://arxiv.org/pdf/2201.11903.pdf and https://arxiv.org/pdf/2305.10601.pdf

"""

from __future__ import annotations

import re
from io import BytesIO
from typing import AsyncIterable
from urllib.parse import urlparse, urlunparse

import fastapi_poe.client
import pdftotext
import requests
from bs4 import BeautifulSoup
from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import Image, Stub, asgi_app
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000

url_regex = re.compile(
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)


def extract_urls(text):
    return url_regex.findall(text)


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
    # Note: many websites seem to block this, needs fixing
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


def parse_pdf_document_from_url(pdf_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(pdf_url)
        with BytesIO(response.content) as f:
            pdf = pdftotext.PDF(f)
        text = "\n\n".join(pdf)
        text = text[:2000]
        return True, text
    except requests.exceptions.MissingSchema:
        return False, ""
    except BaseException:
        return False, ""


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        user_statement = query.query[-1].content.strip()
        print(user_statement)

        urls = extract_urls(user_statement)

        for url in urls:
            if url.endswith(".pdf"):
                _, content = parse_pdf_document_from_url(url)
            else:
                content = extract_readable_text(url)[:3000]  # to fix
            user_statement += "\n{url} contains the following content:"
            user_statement += "\n\n---\n\n"
            user_statement += content
            user_statement += "\n\n---\n\n"

        query.query[-1].content = user_statement

        current_message = ""

        async for msg in stream_request(query, "ChatGPT", query.api_key):
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
            server_bot_dependencies={"ChatGPT": 1}, allow_attachments=False
        )


bot = EchoBot()

image = (
    Image.debian_slim()
    .apt_install("libpoppler-cpp-dev")
    .pip_install(
        "fastapi-poe==0.0.23",
        "pdftotext==2.2.2",
        "requests==2.28.2",
        "beautifulsoup4==4.12.2",
    )
)

stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, allow_without_key=True)
    return app
