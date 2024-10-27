from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from modal import App, Image, asgi_app

IMAGE_URL = (
    "https://images.pexels.com/photos/46254/leopard-wildcat-big-cat-botswana-46254.jpeg"
)


class SampleImageResponseBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        yield fp.PartialResponse(text=f"This is a test image. ![leopard]({IMAGE_URL})")


REQUIREMENTS = ["fastapi-poe==0.0.48"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App("image-response-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = SampleImageResponseBot()
    # see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
    # app = fp.make_app(bot, access_key=<YOUR_ACCESS_KEY>, bot_name=<YOUR_BOT_NAME>)
    app = fp.make_app(bot, allow_without_key=True)
    return app
