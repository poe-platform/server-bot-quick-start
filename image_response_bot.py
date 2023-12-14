from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from modal import Image, Stub, asgi_app

IMAGE_URL = (
    "https://images.pexels.com/photos/46254/leopard-wildcat-big-cat-botswana-46254.jpeg"
)


class SampleImageResponseBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        yield fp.PartialResponse(text=f"This is a test image. ![leopard]({IMAGE_URL})")


REQUIREMENTS = ["fastapi-poe==0.0.25"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("image-response-poe")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    bot = SampleImageResponseBot()
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
