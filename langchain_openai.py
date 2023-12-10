from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe as fp
from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage


class LangchainOpenAIChatBot(fp.PoeBot):
    def __init__(self, OPENAI_API_KEY: str):
        self.chat_model = ChatOpenAI(openai_api_key=OPENAI_API_KEY)

    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        messages = []
        for message in request.query:
            if message.role == "bot":
                messages.append(AIMessage(content=message.content))
            elif message.role == "system":
                messages.append(SystemMessage(content=message.content))
            elif message.role == "user":
                messages.append(HumanMessage(content=message.content))

        response = self.chat_model.predict_messages(messages).content
        yield fp.PartialResponse(text=response)
