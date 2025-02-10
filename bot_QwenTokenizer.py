"""

BOT_NAME="tiktoken"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
ChatGPT

"""

from __future__ import annotations

from typing import AsyncIterable

import fastapi_poe.client
from fastapi_poe import PoeBot, make_app
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import Image, Stub, asgi_app
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000


from transformers import AutoTokenizer

# need to unzip tokenizer.json.zip locally before deployment
# (zipped because the file size is above 10MB)
tokenizer = AutoTokenizer.from_pretrained("./qwen_tokenizer")

class QwenTokenizerBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        last_message = query.query[-1].content
        tokens = tokenizer.encode(last_message, add_special_tokens=False)
        last_message = "\n".join(
            [
                f'{token}\n```text\n{str(tokenizer.decode(token))}\n```\n\n'
                for token in tokens
            ]
        )
        yield self.text_event(last_message)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={},
            allow_attachments=False,  # to update when ready
            introduction_message="Submit a statement for it to be broken down into tokens that ChatGPT reads.",
        )

