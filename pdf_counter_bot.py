from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
import requests
from modal import Image, Stub, asgi_app
from PyPDF2 import PdfReader


class FileDownloadError(Exception):
    pass


def _fetch_pdf_and_count_num_pages(url: str) -> int:
    response = requests.get(url)
    if response.status_code != 200:
        raise FileDownloadError()
    with open("temp_pdf_file.pdf", "wb") as f:
        f.write(response.content)
    reader = PdfReader("temp_pdf_file.pdf")
    return len(reader.pages)


class PDFSizeBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        for message in reversed(request.query):
            for attachment in message.attachments:
                if attachment.content_type == "application/pdf":
                    try:
                        num_pages = _fetch_pdf_and_count_num_pages(attachment.url)
                        yield fp.PartialResponse(
                            text=f"{attachment.name} has {num_pages} pages"
                        )
                    except FileDownloadError:
                        yield fp.PartialResponse(
                            text="Failed to retrieve the document."
                        )
                    return

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(allow_attachments=True)


REQUIREMENTS = ["fastapi-poe==0.0.25", "PyPDF2==3.0.1", "requests==2.31.0"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("pdf-counter-poe")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    bot = PDFSizeBot()
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter examples disable the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    # POE_ACCESS_KEY = ""
    # app = make_app(bot, access_key=POE_ACCESS_KEY)
    app = fp.make_app(bot, allow_without_key=True)
    return app
