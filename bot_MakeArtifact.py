"""

BOT_NAME="MakeArtifact"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

"""

from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from modal import Image, App, asgi_app
from fastapi_poe.types import PartialResponse, ProtocolMessage

import modal
import re

ARTIFACT_REGEX = re.compile(r"<artifact>(.+?)</artifact>", re.DOTALL)


def extract_suggested_replies(raw_output: str) -> list[str]:
    suggested_replies = [
        suggestion.strip() for suggestion in ARTIFACT_REGEX.findall(raw_output)
    ]
    return "".join(suggested_replies)


class GPT35TurboAllCapsBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        
        request.query = [
            {
                "role": "system",
                "content": "You will make a html artifact. Put the html in between <artifact> and </artifact>"
            }
        ] + request.query
        
        current_message = ""

        async for msg in fp.stream_request(
            request, "Claude-3.5-Sonnet", request.access_key
        ):
            current_message += msg.text
            yield msg

        func = modal.Function.lookup("function-upload-shared", "upload_file_by_string")

        html = extract_suggested_replies(current_message)

        if html:
            file_url = func.remote(html, "doc.html")
            yield PartialResponse(text=f'\n\n# [Artifact]({file_url})')

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={"Claude-3.5-Sonnet": 1})


REQUIREMENTS = ["fastapi-poe==0.0.36"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App("MakeArtifacts")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = GPT35TurboAllCapsBot()
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
