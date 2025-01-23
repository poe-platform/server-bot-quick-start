"""

Bot that generates an image from the latest chat message.

Uses Fireworks AI and Stable Diffusion XL.

"""

import asyncio
import io
import os
import random
from typing import AsyncIterable, Optional, Union

import fastapi_poe as fp
import httpx
from fastapi_poe import PoeBot
from fastapi_poe.types import (
    ErrorResponse,
    MetaResponse,
    PartialResponse,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
from modal import App, Image, asgi_app
from PIL import Image as PILImage
from sse_starlette.sse import ServerSentEvent

# TODO: set your bot access key, and fireworks api key, and bot name for this bot to work
# see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
bot_access_key = os.getenv("POE_ACCESS_KEY")
fireworks_api_key = os.getenv("FIREWORKS_API_KEY")
bot_name = ""

NUM_STEPS = 50
ASPECT_RATIO = "1:1"
FIREWORKS_SDXL_ENDPOINT = (
    "https://api.fireworks.ai/inference/v1/image_generation/"
    "accounts/fireworks/models/stable-diffusion-xl-1024-v1-0"
)


class SDXLBot(PoeBot):
    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(enable_multi_bot_chat_prompting=True)

    async def _generate_image_async(
        self, prompt: str, aspect_ratio: Optional[str] = ASPECT_RATIO
    ) -> Optional[PILImage.Image]:
        async with httpx.AsyncClient(timeout=None) as client:
            url = FIREWORKS_SDXL_ENDPOINT
            headers = {
                "Authorization": f"Bearer {fireworks_api_key}",
                "Content-Type": "application/json",
                "Accept": "image/jpeg",
            }
            json_data = {
                "prompt": prompt,
                "steps": NUM_STEPS,
                "seed": random.randint(0, 2**32 - 1),
            }

            if aspect_ratio is not None:
                json_data["aspect_ratio"] = aspect_ratio

            try:
                response = await client.post(url, headers=headers, json=json_data)
                response.raise_for_status()

                image_bytes = io.BytesIO(response.content)
                image = PILImage.open(image_bytes)
                return image

            except Exception as e:
                print(e)
                return None

    async def get_response(
        self, query: QueryRequest
    ) -> AsyncIterable[Union[PartialResponse, ServerSentEvent]]:
        """Uses the latest chat message as a prompt to generate an image."""
        # disable suggested replies
        yield MetaResponse(text="", suggested_replies=False)

        user_message = query.query[-1].content
        inference_task = asyncio.create_task(self._generate_image_async(user_message))

        try:
            inference_task_timer = 0
            while not inference_task.done():
                yield self.replace_response_event(
                    text=f"Generating image... ({inference_task_timer} seconds)"
                )
                await asyncio.sleep(1)
                inference_task_timer += 1

            result = await inference_task
            if isinstance(result, PILImage.Image):
                img_byte_arr = io.BytesIO()
                result.save(img_byte_arr, format=result.format)
                img_byte_arr = img_byte_arr.getvalue()
                attachment_upload_response = await self.post_message_attachment(
                    message_id=query.message_id,
                    file_data=img_byte_arr,
                    filename="image.jpg",
                    is_inline=True,
                )
                if not attachment_upload_response.inline_ref:
                    yield ErrorResponse(
                        text="Error uploading image to Poe.", allow_retry=True
                    )
                    return
                output_md = f"![image.jpg][{attachment_upload_response.inline_ref}]"
                yield PartialResponse(text=output_md, is_replace_response=True)
            else:
                yield ErrorResponse(text="Error generating image.", allow_retry=True)
                return
        except Exception as e:
            yield ErrorResponse(
                text="The bot ran into an unexpected error.",
                raw_response=e,
                allow_retry=True,
            )
            return


REQUIREMENTS = ["fastapi-poe", "pillow"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .env({"FIREWORKS_API_KEY": fireworks_api_key, "POE_ACCESS_KEY": bot_access_key})
)
app = App("sdxlbot-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = SDXLBot()
    app = fp.make_app(
        bot,
        access_key=bot_access_key,
        bot_name=bot_name,
        allow_without_key=not (bot_access_key and bot_name),
    )
    return app
