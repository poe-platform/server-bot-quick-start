from __future__ import annotations

from typing import AsyncIterable

from fastapi_poe import PoeBot
from fastapi_poe.types import PartialResponse, QueryRequest
from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage


class LangchainOpenAIChatBot(PoeBot):
    def __init__(self, OPENAI_API_KEY: str):
        self.chat_model = ChatOpenAI(openai_api_key=OPENAI_API_KEY)

    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        messages = []
        for message in request.query:
            if message.role == "bot":
                messages.append(AIMessage(content=message.content))
            elif message.role == "system":
                messages.append(SystemMessage(content=message.content))
            elif message.role == "user":
                messages.append(HumanMessage(content=message.content))

        response = self.chat_model.predict_messages(messages).content
        yield PartialResponse(text=response)
