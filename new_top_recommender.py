"""
Example PoeBot that:
1) Takes a user-uploaded image (ideally a full-body photo of a person).
2) Asks Claude-3.5-Sonnet to recommend a new top (e.g., shirt or jacket).
3) Asks Imagen3-Fast to generate an image of that new top.
5) Returns the final recommended image.
"""

from __future__ import annotations

import os
from typing import AsyncIterable

import fastapi_poe as fp
from modal import App, Image, asgi_app

# TODO: set your bot access key and bot name for full functionality
# see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
bot_access_key = os.getenv("POE_ACCESS_KEY")
bot_name = ""


class OutfitRecommenderBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        """
        1) Find the *latest* user image if present.
        2) Call Claude-3.5-Sonnet: "Analyze the person's outfit & recommend a new top."
        3) Take Claude's recommended top text & call Imagen3-Fast to generate an image of that top.
        5) Return the generated image of recommended top to user.
        """

        # 1) Identify user's image (if any)
        user_image = None
        for message in reversed(request.query):
            if message.role == "user" and message.attachments:
                # Just pick the first image we find
                for attachment in message.attachments:
                    if attachment.content_type.startswith("image/"):
                        user_image = attachment
                        break
            if user_image:
                break

        if not user_image:
            # If there's no image, we let the user know that we need one
            yield fp.PartialResponse(
                text="Please attach an image of your outfit so I can suggest a new top!"
            )
            return

        # 2) Ask Claude-3.5-Sonnet to analyze the photo and recommend a top
        # We'll craft a custom message for Claude including a reference to the user image
        # We do so by copying the original request but overriding the final user message content
        claude_request_content = (
            "Please analyze the person's outfit accordingly:\n"
            "1) They want to change the top they are wearing (e.g., a shirt or jacket).\n"
            "2) Suggest a single new top style, with some details, e.g. color or design.\n"
            "Keep your response concise and to the point."
            "NOTE: The user's attached image is their current outfit."
        )
        last_message = request.query[-1]
        last_message_with_claude_query = last_message.model_copy(
            update={"content": claude_request_content}
        )
        claude_request = request.model_copy(
            update={"query": [last_message_with_claude_query]}
        )

        recommended_top = None
        recommended_top_text = ""
        async for msg in fp.stream_request(
            claude_request, "Claude-3.5-Sonnet", request.access_key
        ):
            if msg.text:
                recommended_top_text += msg.text
            yield fp.PartialResponse(text=msg.text)

        recommended_top = recommended_top_text.strip()
        if not recommended_top:
            yield fp.ErrorResponse(
                text="I was unable to get a clothing recommendation from Claude."
            )
            return

        # 3) Ask Imagen3-Fast to generate an image of the recommended top
        imagen_request = request.model_copy(deep=True)
        imagen_request.query[-1].content = (
            f"Please create an image of a {recommended_top} only. White background."
        )

        yield fp.PartialResponse(text="\n\nGenerating an example image...")

        generated_image = None
        async for msg in fp.stream_request(
            imagen_request, "Imagen3-Fast", request.access_key
        ):
            if msg.attachment:
                # If Imagen3-Fast responds with an attachment, pick it out
                generated_image = msg.attachment

        if not generated_image:
            yield fp.ErrorResponse(
                text="The Imagen3-Fast bot did not return an image of the top."
            )
            return

        # Now attach the final image
        attachment_response = await self.post_message_attachment(
            message_id=request.message_id,
            download_url=generated_image.url,
            is_inline=True,
        )
        yield fp.PartialResponse(
            text=f"\n\nHere's an image of the recommended top![new_top][{attachment_response.inline_ref}]"
        )

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        """
        - We turn on attachments so we can receive the user's image.
        - We also want to call 2 other bots (Claude-3.5-Sonnet, Imagen3-Fast).
        """
        return fp.SettingsResponse(
            allow_attachments=True,
            server_bot_dependencies={"Claude-3.5-Sonnet": 1, "Imagen3-Fast": 1},
        )


# Requirements for our container
REQUIREMENTS = ["fastapi-poe>=0.0.57"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .env({"POE_ACCESS_KEY": bot_access_key})
)
app = App("outfit-recommender-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = OutfitRecommenderBot()
    poe_app = fp.make_app(
        bot,
        access_key=bot_access_key,
        bot_name=bot_name,
        allow_without_key=not (bot_access_key and bot_name),
    )
    return poe_app
