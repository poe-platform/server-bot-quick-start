"""

BOT_NAME="RunPythonCode"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
assert False

"""

import os
import re
from typing import AsyncIterable

import fastapi_poe.client
import modal
from fastapi_poe import MetaResponse, PoeBot, make_app
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import App, Image, asgi_app
from sse_starlette.sse import ServerSentEvent

fastapi_poe.client.MAX_EVENT_COUNT = 10000

# https://modalbetatesters.slack.com/archives/C031Z7H15DG/p1675177408741889?thread_ts=1675174647.477169&cid=C031Z7H15DG
modal.app._is_container_app = False


INTRODUCTION_MESSAGE = """
This bot will execute Python code.

````
```python
print("Hello World!")
```
````

Try copying the above, paste it, and reply.
""".strip()


RESPONSE_PYTHON_CODE_MISSING = """
No Python code was found in your previous message.

````
```python
print("Hello World!")
```
````

Try copying the above, paste it, and reply.
""".strip()


def format_output(captured_output, captured_error="") -> str:
    lines = []

    if captured_output:
        line = f"\n```output\n{captured_output}\n```"
        lines.append(line)

    if captured_error:
        line = f"\n```error\n{captured_error}\n```"
        lines.append(line)

    return "\n".join(lines)


def extract_code(reply):
    pattern = r"```python([\s\S]*?)```"
    matches = re.findall(pattern, reply)
    code = "\n\n".join(matches)
    if code:
        return code
    return reply


class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[ServerSentEvent]:

        # disable suggested replies
        yield MetaResponse(
            text="",
            content_type="text/markdown",
            linkify=True,
            refetch_settings=False,
            suggested_replies=False,
        )

        while request.query:
            code = request.query[-1].content
            if """```python""" in code:
                break
            request.query.pop()

        if len(request.query) == 0:
            yield self.text_event(RESPONSE_PYTHON_CODE_MISSING)
            return

        print("user_statement")
        print(code)
        code = request.query[-1].content
        code = extract_code(code)
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
            introduction_message=INTRODUCTION_MESSAGE,
        )


bot = EchoBot()

image = (
    Image.debian_slim()
    .pip_install("fastapi-poe==0.0.37")
    .env({"POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"]})
)

app = App("poe-bot-quickstart")


@app.function(image=image, container_idle_timeout=1200)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
