"""

Sample bot that shows the query sent to the bot.

"""

from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from devtools import PrettyFormat
from modal import App, Image, asgi_app, exit

pformat = PrettyFormat(width=85)


class LogBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        yield fp.PartialResponse(text="```python\n" + pformat(request) + "\n```")

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            allow_attachments=True, enable_image_comprehension=True
        )


REQUIREMENTS = ["fastapi-poe==0.0.47", "devtools==0.12.2"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App(name="log-bot-poe", image=image)


@app.cls(image=image)
class Model:
    # See https://creator.poe.com/docs/quick-start#integrating-with-poe to find these values.
    access_key: str | None = None  # REPLACE WITH YOUR ACCESS KEY
    bot_name: str | None = None  # REPLACE WITH YOUR BOT NAME

    @exit()
    def sync_settings(self):
        """Syncs bot settings on server shutdown."""
        if self.bot_name and self.access_key:
            try:
                fp.sync_bot_settings(self.bot_name, self.access_key)
            except Exception:
                print("\n*********** Warning ***********")
                print(
                    "Bot settings sync failed. For more information, see: https://creator.poe.com/docs/server-bots-functional-guides#updating-bot-settings"
                )
                print("\n*********** Warning ***********")

    @asgi_app()
    def fastapi_app(self):
        bot = LogBot()
        if not self.access_key:
            print(
                "Warning: Running without an access key. Please remember to set it before production."
            )
            app = fp.make_app(bot, allow_without_key=True)
        else:
            app = fp.make_app(bot, access_key=self.access_key)
        return app


@app.local_entrypoint()
def main():
    Model().run.remote()
