from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from modal import Image, Mount, Stub, asgi_app


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


REQUIREMENTS = ["fastapi-poe==0.0.34"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("video-bot")


def get_app():
    access_key = "<put your access key here>"
    bot = VideoBot(access_key=access_key)
    return fp.make_app(bot)


@stub.function(
    image=image, mounts=[Mount.from_local_dir("./assets", remote_path="/root/assets")]
)
@asgi_app()
def fastapi_app():
    return get_app()
