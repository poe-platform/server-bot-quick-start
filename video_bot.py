from __future__ import annotations

import os
from typing import AsyncIterable

import fastapi_poe as fp
from modal import App, Image, Mount, asgi_app


class VideoBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        with open("/root/assets/tiger.mp4", "rb") as file:
            file_data = file.read()
        await self.post_message_attachment(
            message_id=request.message_id, file_data=file_data, filename="tiger.mp4"
        )
        yield fp.PartialResponse(text="Attached a video.")


REQUIREMENTS = ["fastapi-poe==0.0.46"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .env({"POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"]})
)
app = App("video-bot")


@app.function(
    image=image, mounts=[Mount.from_local_dir("./assets", remote_path="/root/assets")]
)
@asgi_app()
def fastapi_app():
    bot = VideoBot()
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter examples disable the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    POE_ACCESS_KEY = os.environ["POE_ACCESS_KEY"]
    app = fp.make_app(bot, access_key=POE_ACCESS_KEY)
    return app
