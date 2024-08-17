from __future__ import annotations

import os
from typing import AsyncIterable

import fastapi_poe as fp
from modal import App, Image, Mount, asgi_app, exit


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


REQUIREMENTS = ["fastapi-poe==0.0.47"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .env({"POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"]})
)
app = App(
    name="video-bot",
    image=image,
    mounts=[Mount.from_local_dir("./assets", remote_path="/root/assets")],
)


@app.cls(image=image)
class Model:
    # See https://creator.poe.com/docs/quick-start#integrating-with-poe to find these values.
    access_key: str | None = os.environ[
        "POE_ACCESS_KEY"
    ]  # REPLACE WITH YOUR ACCESS KEY
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
        bot = VideoBot()
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
