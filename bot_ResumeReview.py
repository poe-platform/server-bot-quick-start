"""

BOT_NAME="ResumeReview"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
(download this and upload)
https://pjreddie.com/static/Redmon%20Resume.pdf

"""

from __future__ import annotations

import os
from io import BytesIO
from typing import AsyncIterable

import fastapi_poe.client
import pdftotext
import requests
from docx import Document
from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import (
    ProtocolMessage,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
from modal import Image, Stub, asgi_app
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000


async def parse_pdf_document_from_url(pdf_url: str) -> tuple[bool, str]:
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


async def parse_pdf_document_from_docx(docx_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(docx_url)
        with BytesIO(response.content) as f:
            document = Document(f)
        text = [p.text for p in document.paragraphs]
        text = "\n\n".join(text)
        text = text[:2000]
        return True, text
    except requests.exceptions.MissingSchema as e:
        print(e)
        return False, ""
    except BaseException as e:
        print(e)
        return False, ""


# This is now the system prompt for poe.com/ResumeReviewTool
RESUME_SYSTEM_PROMPT = """
You will be given text from a resume, extracted with Optical Character Recognition.
You will suggest specific improvements for a resume, by the standards of US/Canada industry.

Do not give generic comments.
All comments has to quote the relevant sentence in the resume where there is an issue.

You will only check the resume text for formatting errors, and suggest improvements to the bullet points.
You will not evaluate the resume, as your role is to suggest improvements.
You will focus on your comments related to tech and engineering content.
Avoid commenting on extra-curricular activities.


The following are the formmatting errors to check.
If there is a formatting error, quote the original text, and suggest how should it be rewritten.
Only raise these errors if you are confident that this is an error.

- Inconsistent date formats. Prefer Mmm YYYY for date formats.
- Misuse of capitalization. Do not capitalize words that are not capitalized in professional communication.
- Misspelling of technical terminologies. (Ignore if the error is likely to due OCR parsing inaccuracies.)
- The candidate should not explictly label their level of proficiency in the skills section.


Suggest improvements to bullet points according to these standards.
Quote the original text (always), and suggest how should it be rewritten.

- Emulate the Google XYZ formula - e.g. Accomplished X, as measured by Y, by doing Z
- Ensure the bullet points are specific.
  It shows exactly what feature or system the applicant worked on, and their exact contribution.
- Specify the exact method or discovery where possible.
- Ensure the metrics presented by the resume can be objectively measured.
  Do not use unmeasurable metrics like “effectiveness” or “efficiency”.
- You may assume numbers of the metrics in your recommendations.
- You may assume additional facts not mentioned in the bullet points in your recommendations.
- Prefer simpler sentence structures and active language
    - Instead of "Spearheaded development ...", write "Developed ..."
    - Instead of "Utilized Python to increase the performance of ...", write "Increased the performance of ... with Python"

Please suggest only the most important improvements to the resume. All your suggestions should quote from the resume.
Each suggestion should start with "Suggestion X" (e.g. Suggestion 1), and followed by two new lines.
In the suggestion, quote from the resume, and write what you suggest to improve.
At the end of each suggestion, add a markdown horizontal rule, which is `---`.
Do not reproduce the full resume unless asked. You will not evaluate the resume, as your role is to suggest improvements.
"""


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        for query_message in query.query:
            # replace attachment with text
            if (
                query_message.attachments
                and query_message.attachments[0].content_type == "application/pdf"
            ):
                content_url = query_message.attachments[0].url
                print("parsing pdf", content_url)
                success, resume_string = await parse_pdf_document_from_url(content_url)
                query_message.content += (
                    f"\n\n This is the attached resume: {resume_string}"
                )

            elif query_message.attachments and query_message.attachments[
                0
            ].content_type.endswith("document"):
                content_url = query_message.attachments[0].url
                print("parsing docx", content_url)
                success, resume_string = await parse_pdf_document_from_docx(content_url)
                query_message.content += (
                    f"\n\n This is the attached resume: {resume_string}"
                )

            query_message.attachments = []

        query.query = [
            ProtocolMessage(role="system", content=RESUME_SYSTEM_PROMPT)
        ] + query.query

        current_message = ""
        async for msg in stream_request(query, "ChatGPT", query.api_key):
            # Note: See https://poe.com/ResumeReviewTool for the prompt
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
            server_bot_dependencies={"ChatGPT": 1},
            allow_attachments=True,  # to update when ready
            introduction_message="Please upload your resume (pdf, docx) and say 'Review this'.",
        )


bot = EchoBot()

image = (
    Image.debian_slim()
    .apt_install("libpoppler-cpp-dev")
    .apt_install("tesseract-ocr-eng")
    .pip_install(
        "fastapi-poe==0.0.23",
        "huggingface-hub==0.16.4",
        "requests==2.31.0",
        "pdftotext==2.2.2",
        "Pillow==9.5.0",
        "openai==0.27.8",
        "pytesseract==0.3.10",
        "python-docx",
    )
).env({"POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"]})

stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
