"""

Sample bot that wraps GPT-3.5-Turbo but makes responses use all-caps.

"""

from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from modal import App, Image, asgi_app, exit


class GPT35TurboAllCapsBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        async for msg in fp.stream_request(
            request, "GPT-3.5-Turbo", request.access_key
        ):
            yield msg.model_copy(update={"text": msg.text.upper()})

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(server_bot_dependencies={"GPT-3.5-Turbo": 1})


REQUIREMENTS = ["fastapi-poe==0.0.47"]
image = Image.debian_slim().pip_install(*REQUIREMENTS)
app = App(name="turbo-allcaps-poe", image=image)


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
        bot = GPT35TurboAllCapsBot()
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
