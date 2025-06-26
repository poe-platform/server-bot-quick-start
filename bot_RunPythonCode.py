"""

BOT_NAME="RunPythonCode"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
assert False

"""

import re
from typing import AsyncIterable

import fastapi_poe.client
import modal
from fastapi_poe import MetaResponse, PoeBot
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import Image, Sandbox
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


IMAGE_EXEC = (
    Image
    .debian_slim()
    .apt_install("curl", "git", "ripgrep")
    .pip_install(
        "ipython",
        "scipy",
        "matplotlib",
        "scikit-learn",
        "pandas",
        "ortools",
        "openai",
        "requests",
        "beautifulsoup4",
        "newspaper3k",
        "XlsxWriter",
        "docx2txt",
        "markdownify",
        "pdfminer.six",
        "Pillow",
        "sortedcontainers",
        "intervaltree",
        "geopandas",
        "basemap",
        "tiktoken",
        "basemap-data-hires",
        "yfinance",
        "dill",
        "seaborn",
        "openpyxl",
        "cartopy",
        "sympy",
    )
    .pip_install(
        ["torch", "torchvision", "torchaudio"],
        index_url="https://download.pytorch.org/whl/cpu",
    )
    .pip_install(
        "tensorflow",
        "keras",
        "nltk",
        "spacy",
        "opencv-python-headless",
        "feedparser",
        "wordcloud",
        "opencv-python",
        "transformers",
    )
)



class RunPythonCodeBot(PoeBot):
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

        nfs = modal.NetworkFileSystem.from_name(f"vol-{request.user_id[::-1][:32][::-1]}", create_if_missing=True)
        # upload python script
        with open(f"{request.conversation_id}.py", "w") as f:
            f.write(code)
        nfs.add_local_file(
            f"{request.conversation_id}.py", f"{request.conversation_id[::-1][:32][::-1]}.py"
        )

        # execute code
        sb = Sandbox.create(
            "bash",
            "-c",
            f"cd /cache && python {request.conversation_id[::-1][:32][::-1]}.py",
            image=IMAGE_EXEC,
            network_file_systems={"/cache": nfs},
        )
        sb.wait()

        print("sb.returncode", sb.returncode)

        output = sb.stdout.read()
        error = sb.stderr.read()

        if not output and not error:
            yield self.text_event("No output or error recorded.")
            return

        if output:
            if len(output) > 5000:
                yield self.text_event(
                    "There is too much output, this is the partial output."
                )
                output = output[:5000]
            reply_string = format_output(output)
            yield self.text_event(reply_string)

        if error:
            if len(error) > 5000:
                yield self.text_event(
                    "There is too much error, this is the partial error."
                )
                error = error[:5000]
            reply_string = format_output(error)
            yield self.text_event(reply_string)


    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={},
            allow_attachments=False,  # to update when ready
            introduction_message=INTRODUCTION_MESSAGE,
        )

