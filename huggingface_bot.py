"""

Bot that lets you talk to conversational models available on HuggingFace.

"""
from __future__ import annotations

from typing import AsyncIterable

from fastapi_poe import PoeBot
from fastapi_poe.types import QueryRequest
from huggingface_hub import InferenceClient
from sse_starlette.sse import ServerSentEvent


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

    def __init__(self, model: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if model is None:
            raise ValueError("Unsupported model: {model}")
        self.client = InferenceClient(model=model)

    async def query_hf_model(
        self, current_message_text, bot_messages: list[str], user_messages: list[str]
    ) -> tuple[int, dict]:
        return self.client.conversational(
            current_message_text, bot_messages, user_messages
        )

    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        user_messages = []
        bot_messages = []
        for message in query.query:
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
            yield self.text_event("Incorrect number of user and bot messages")
        current_message_text = user_messages.pop()

        response_data = await self.query_hf_model(
            current_message_text, bot_messages, user_messages
        )
        yield self.text_event(response_data["generated_text"])
