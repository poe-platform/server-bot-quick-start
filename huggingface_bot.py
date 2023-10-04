"""

Bot that lets you talk to conversational models available on HuggingFace.

"""
from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterable

from fastapi_poe import PoeBot
from fastapi_poe.types import PartialResponse, QueryRequest
from huggingface_hub import AsyncInferenceClient
from huggingface_hub.inference._types import ConversationalOutput


@dataclass
class HuggingFaceBot(PoeBot):
    """This bot uses the HuggingFace Inference API.

    By default, it uses the HuggingFace public Inference API, but you can also
    use this class with a self hosted Inference Endpoint.
    For more information on how to create a self hosted endpoint, see:
    https://huggingface.co/blog/inference-endpoints

    Arguments:
        - model: either the name of the model (if you want to use the public API)
        or a link to your hosted inference endpoint.

    """

    model: str

    def __post_init__(self) -> None:
        self.client = AsyncInferenceClient(model=self.model)

    async def query_hf_model(
        self,
        current_message_text: str,
        bot_messages: list[str],
        user_messages: list[str],
    ) -> ConversationalOutput:
        return await self.client.conversational(
            current_message_text, bot_messages, user_messages
        )

    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        user_messages = []
        bot_messages = []
        for message in request.query:
            if message.role == "user":
                if len(user_messages) == len(bot_messages):
                    user_messages.append(message.content)
                else:
                    user_messages[-1] = user_messages[-1] + f"\n{message.content}"
            elif message.role == "bot":
                bot_messages.append(message.content)
            else:
                raise ValueError(f"unknown role {message.role}")

        if len(user_messages) != len(bot_messages) + 1:
            yield PartialResponse(text="Incorrect number of user and bot messages")
        current_message_text = user_messages.pop()

        response_data = await self.query_hf_model(
            current_message_text, bot_messages, user_messages
        )
        yield PartialResponse(text=response_data["generated_text"])
