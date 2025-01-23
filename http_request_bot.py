"""

Sample bot that shows how to access the HTTP request.

"""

from __future__ import annotations

import os
import re
from typing import AsyncIterable

import fastapi_poe as fp
from devtools import PrettyFormat
from modal import App, Image, asgi_app

pformat = PrettyFormat(width=85)

# TODO: set your bot access key and bot name for full functionality
# see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
bot_access_key = os.getenv("POE_ACCESS_KEY")
bot_name = ""


class HttpRequestBot(fp.PoeBot):
    async def get_response_with_context(
        self, request: fp.QueryRequest, context: fp.RequestContext
    ) -> AsyncIterable[fp.PartialResponse]:

        context_string = pformat(context)
        context_string = re.sub(r"Bearer \w+", "Bearer [REDACTED]", context_string)
        context_string = re.sub(
            r"b'host',\s*b'([^']*)'", r"b'host', b'[REDACTED_HOST]'", context_string
        )

        yield fp.PartialResponse(text="```python\n" + context_string + "\n```")


REQUIREMENTS = ["fastapi-poe", "devtools==0.12.2"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .env({"POE_ACCESS_KEY": bot_access_key})
)
app = App("http-request")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = HttpRequestBot()
    app = fp.make_app(
        bot,
        access_key=bot_access_key,
        bot_name=bot_name,
        allow_without_key=not (bot_access_key and bot_name),
    )
    return app
