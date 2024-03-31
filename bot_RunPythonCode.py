"""

BOT_NAME="RunPythonCode"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
assert False

"""

import os
from typing import AsyncIterable

import fastapi_poe.client
import modal
from fastapi_poe import PoeBot, make_app
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import Image, Stub, asgi_app
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000

# https://modalbetatesters.slack.com/archives/C031Z7H15DG/p1675177408741889?thread_ts=1675174647.477169&cid=C031Z7H15DG
modal.app._is_container_app = False


def format_output(captured_output, captured_error="") -> str:
    lines = []

    if captured_output:
        line = f"\n```output\n{captured_output}\n```"
        lines.append(line)

    if captured_error:
        line = f"\n```error\n{captured_error}\n```"
        lines.append(line)

    return "\n".join(lines)


def strip_code(code):
    if len(code.strip()) < 6:
        return code
    code = code.strip()
    if code.startswith("```") and code.endswith("```"):
        code = code[3:-3]
    return code


class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        print("user_statement")
        print(query.query[-1].content)
        code = query.query[-1].content
        code = strip_code(code)
        try:
            f = modal.Function.lookup("run-python-code-shared", "execute_code")
            captured_output = f.remote(code)  # need async await?
        except modal.exception.TimeoutError:
            yield self.text_event("Time limit exceeded.")
            return
        if len(captured_output) > 5000:
            yield self.text_event(
                "There is too much output, this is the partial output."
            )
            captured_output = captured_output[:5000]
        reply_string = format_output(captured_output)
        if not reply_string:
            yield self.text_event("No output or error recorded.")
            return
        yield self.text_event(reply_string)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={},
            allow_attachments=False,  # to update when ready
            introduction_message="Please send executable Python code.",
        )


bot = EchoBot()

image = (
    Image.debian_slim()
    .pip_install("fastapi-poe==0.0.23")
    .env({"POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"]})
)

stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
