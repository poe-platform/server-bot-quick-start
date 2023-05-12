"""

Sample bot that uses LangChain to interact with ChatGPT.

You can use this as a sample if you want to build your own bot on top of an existing LLM.

"""

import asyncio
from dataclasses import dataclass
from typing import AsyncIterable

from fastapi_poe import PoeBot
from fastapi_poe.types import QueryRequest
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.callbacks.manager import AsyncCallbackManager
from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from sse_starlette.sse import ServerSentEvent

template = """You are the CatBot. \
You will respond to every message as if you were a cat \
and will always stay in character as a lazy, easily distracted cat. \
Be verbose in your responses so that you get your point across."""


@dataclass
class LangCatBot(PoeBot):
    openai_key: str

    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        messages = [SystemMessage(content=template)]
        for message in query.query:
            if message.role == "bot":
                messages.append(AIMessage(content=message.content))
            elif message.role == "user":
                messages.append(HumanMessage(content=message.content))
        handler = AsyncIteratorCallbackHandler()
        chat = ChatOpenAI(
            openai_api_key=self.openai_key,
            streaming=True,
            callback_manager=AsyncCallbackManager([handler]),
            temperature=0,
        )
        asyncio.create_task(chat.agenerate([messages]))
        async for token in handler.aiter():
            yield self.text_event(token)
