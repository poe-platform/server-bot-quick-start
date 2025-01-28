from __future__ import annotations

import os
from typing import AsyncIterable

import fastapi_poe as fp
from modal import App, Image, Mount, asgi_app

# TODO: set your bot access key and bot name for full functionality
# see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
bot_access_key = os.getenv("POE_ACCESS_KEY")
bot_name = ""


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


REQUIREMENTS = ["fastapi-poe"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .env({"POE_ACCESS_KEY": bot_access_key})
)
app = App(
    name="video-bot",
    image=image,
    mounts=[Mount.from_local_dir("./assets", remote_path="/root/assets")],
)


@app.function(
    image=image, mounts=[Mount.from_local_dir("./assets", remote_path="/root/assets")]
)
@asgi_app()
def fastapi_app():
    bot = VideoBot()
    app = fp.make_app(
        bot,
        access_key=bot_access_key,
        bot_name=bot_name,
        allow_without_key=not (bot_access_key and bot_name),
    )
    return app
