"""

Sample bot that shows the query sent to the bot.

"""

from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from devtools import PrettyFormat
from modal import App, Image, asgi_app

pformat = PrettyFormat(width=85)


class LogBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        request.access_key = "redacted"
        request.api_key = "redacted"
        yield fp.PartialResponse(text="```python\n" + pformat(request) + "\n```")

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            allow_attachments=True, enable_image_comprehension=True
        )


REQUIREMENTS = ["fastapi-poe==0.0.48", "devtools==0.12.2"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App("log-bot-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = LogBot()
    # see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
    # app = fp.make_app(bot, access_key=<YOUR_ACCESS_KEY>, bot_name=<YOUR_BOT_NAME>)
    app = fp.make_app(bot, allow_without_key=True)
    return app
