"""

Note: inactive

BOT_NAME="ResumeReviewEx"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
(download this and upload)
https://pjreddie.com/static/Redmon%20Resume.pdf

"""

from __future__ import annotations

import os
from io import BytesIO
from typing import AsyncIterable

import pytesseract
from PIL import Image as PILImage
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


async def parse_image_document_from_url(image_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(image_url.strip())
        img = PILImage.open(BytesIO(response.content))

        custom_config = "--psm 4"
        text = pytesseract.image_to_string(img, config=custom_config)
        text = text[:10000]
        return True, text
    except BaseException as e:
        print(e)
        return False, ""


# Unimplemented guidelines
# - For date ranges, use en dashes (–), not hyphens (-) or the word "to".
# - Do not state how many people you worked with.
# - Specify what you exactly did.


RESUME_SUFFIX_PROMPT = """
You will review the attached image scan of a resume.

You will iterate over the following guidelines and evaluate whether the resume meets the guidelines.


# Layout

- Use a single column layout.
- The font size should be at least 11.
- Do not add additional indentation to your sections and bullet points.
- The sections and section entries should be left-aligned.
- The dates should be right-aligned.
- Bullet point text should not be justified.
- Your bullet points should not go further right than your dates.
- Ensure sufficient vertical and horizontal margins.
- Ensure sufficient and consistent line spacing between bullet points.
- Ensure sufficient and consistent line spacing between sections/subsections.


# Formatting

- Use Mmm YYYY to format the dates.
- Do not specify the days of the year.
- For date ranges, ensure that there is a space before and after the en dashes.
- Use "Present" if currently working at a job or project.
- Use a modern, easy-to-read font.
- Hyperlinks should be black in color.
- Avoid excessive bolding in bullet points.


# Content

- Do not include your photo in your resume.
- Do not include your identification number, address or birth date in your resume.
- Use standard capitalization and nomenclature.
- Acronyms (except the well-known acronyms) should be fully spelled out.
- Avoid repeating the same verb in the bullet points from the same section.


# Bullet points

- Begin with a verb, in past tense.
- Emphasize your accomplishments first.
- Improvements, if mentioned, should be quantified with an objective, precise and measurable metric.


Reply in the following format

(If the user did not upload an image of their resume, first remind them to upload an image of their resume.)

# Layout

| Guideline | Analysis | OK |
| --------------------------------------------- | -------------------------------------------------------- | -- |
| Use a single column layout. | The resume uses a single column layout. | ✅ |
| Bullet point font size should be at least 11. | As the image is not given, the font size could not be estimated. | ❔ |
(and so on)

# Formatting
| Guideline | Analysis | OK |
| --------------------------------------------- | -------------------------------------------------------- | -- |
| Use Mmm YYYY to format the dates. | The period in Jun. 2022 is not necessary. | ❌ |
(and so on)

# Content

| Guideline | Analysis | OK |
| --------------------------------------------- | -------------------------------------------------------- | -- |
| Do not include your photo in your resume. | The resume does not have a photo | ✅ |
(and so on)

# Bullet points

> Developed a tool to review resumes. (Cite the bullet point FROM THE RESUME. DO NOT HALLUCINATE.)

| Guideline | Analysis | OK |
| --------------------------------------------- | -------------------------------------------------------- | -- |
| Begin with a verb, in past tense. | The bullet point began with "Developed". | ✅ |
(and so on)

> Collected all the job descriptions. (Cite the bullet point FROM THE RESUME. DO NOT HALLUCINATE.)
| Guideline | Analysis | OK |
| --------------------------------------------- | -------------------------------------------------------- | -- |
| Begin with a verb, in past tense. | The bullet point began with "Collected". | ✅ |
(and so on)


---


REMINDER:
- If there is an issue, you will always cite the relevant part of the resume.
- The bullet points being cited MUST BE FROM THE RESUME. DO NOT INVENT THE BULLET POINT.
- You will always follow the reply format (Markdown table).
"""


class EchoBot(PoeBot):
    async def get_response(self, request: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        original_message_id = request.message_id
        
        for query_message in request.query:
            # possible attachment inputs - docx, pdf OR png (enforce one attachment)
            #   Only supporting (one) png for now, until Poe supports sending images without cloudinary
            # attachment for the bot - text AND png
            # output - attachments: transcript.txt, analysis.txt
            #   Only the attachments for now

            if not query_message.content:
                query_message.content = " "
            resume_strings = []

            if (
                query_message.attachments
            ):
                for attachment in query_message.attachments:
                    if attachment.content_type.startswith("image/"):
                        print("parsing image", attachment.url)
                        success, resume_string = await parse_image_document_from_url(
                            attachment.url
                        )
                        # query_message.content += (
                        #     f"\n\n This is the extracted text from the image: <text>\n{resume_string}\n<\text>"
                        # )
                        resume_strings.append(resume_string)

        if resume_strings and False:
            with open("transcript.txt", "w") as f:
                f.write("\n\n".join(resume_strings))

            with open("transcript.txt", "rb") as f:
                txt_data = f.read()

            _ = await self.post_message_attachment(
                os.environ["POE_ACCESS_KEY"],
                original_message_id,
                file_data=txt_data,
                filename="transcript.txt",
                is_inline=False,
            )

        query_message.content += "\n\n" + RESUME_SUFFIX_PROMPT

        current_message = ""
        async for msg in stream_request(request, "RekaFlash", request.api_key):
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
            server_bot_dependencies={"RekaFlash": 1},
            allow_attachments=True,  # to update when ready
            introduction_message="Please upload a screenshot of your resume.",
        )


bot = EchoBot()

image = (
    Image.debian_slim()
    .apt_install("libpoppler-cpp-dev")
    .apt_install("tesseract-ocr-eng")
    .pip_install(
        "fastapi-poe==0.0.32",
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
