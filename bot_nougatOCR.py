"""

BOT_NAME="nougatOCR"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
https://pjreddie.com/static/Redmon%20Resume.pdf

"""

from __future__ import annotations

import os
from typing import AsyncIterable

import fastapi_poe.client
import modal
from fastapi_poe import PoeBot, make_app
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import Image, Stub, asgi_app
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000


# https://modalbetatesters.slack.com/archives/C031Z7H15DG/p1675177408741889?thread_ts=1675174647.477169&cid=C031Z7H15DG
modal.app._is_container_app = False


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        if (
            query.query[-1].attachments
            and query.query[-1].attachments[0].content_type == "application/pdf"
        ):
            content_url = query.query[-1].attachments[0].url
            yield self.text_event(
                "PDF attachment received. Please wait while we convert ..."
            )
        else:
            yield self.replace_response_event("PDF attachment not found.")

        try:
            f = modal.Function.lookup("ocr-shared", "nougat_ocr")
            captured_output = f.remote(content_url)  # need async await?
        except modal.exception.TimeoutError:
            yield self.replace_response_event("Time limit exceeded.")
            return

        yield self.replace_response_event(captured_output)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={},
            allow_attachments=True,
            introduction_message="Please upload your document (pdf).",
        )


bot = EchoBot()

image = (
    Image.debian_slim()
    .apt_install("libpoppler-cpp-dev")
    .apt_install("tesseract-ocr-eng")
    .pip_install("fastapi-poe==0.0.23")
).env({"POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"]})

stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
