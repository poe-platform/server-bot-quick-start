"""

Sample bot that shows how to access the HTTP request.

"""
from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from modal import Image, Stub, asgi_app


class HttpRequestBot(fp.PoeBot):
    async def get_response_with_context(
        self, request: fp.QueryRequest, context: fp.RequestContext
    ) -> AsyncIterable[fp.PartialResponse]:
        request_url = context.http_request.url
        query_params = context.http_request.query_params
        yield fp.PartialResponse(
            text=f"The request url is: {request_url}, query params are: {query_params}"
        )


REQUIREMENTS = ["fastapi-poe==0.0.31"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
stub = Stub("http-request")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    bot = HttpRequestBot()
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
