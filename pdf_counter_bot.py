from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
import requests
from modal import App, Image, asgi_app
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
        yield fp.PartialResponse(
            text="Iterating over the pdfs uploaded in this conversation ..."
        )
        for message in reversed(request.query):
            for attachment in message.attachments:
                if attachment.content_type == "application/pdf":
                    try:
                        num_pages = _fetch_pdf_and_count_num_pages(attachment.url)
                        yield fp.PartialResponse(
                            text=f"{attachment.name} has {num_pages} pages.\n"
                        )
                    except FileDownloadError:
                        yield fp.PartialResponse(
                            text="Failed to retrieve the document."
                        )

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(allow_attachments=True)


REQUIREMENTS = ["fastapi-poe==0.0.48", "PyPDF2==3.0.1", "requests==2.31.0"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App("pdf-counter-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = PDFSizeBot()
    # see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
    # app = fp.make_app(bot, access_key=<YOUR_ACCESS_KEY>, bot_name=<YOUR_BOT_NAME>)
    app = fp.make_app(bot, allow_without_key=True)
    return app
