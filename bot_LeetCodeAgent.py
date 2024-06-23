"""

BOT_NAME="LeetCodeAgent"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
(copy some leetcode problem)

"""

from __future__ import annotations

import os
import re
import textwrap
from typing import AsyncIterable

import modal
import requests
from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import (
    Attachment,
    PartialResponse,
    ProtocolMessage,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
import fastapi_poe as fp
from modal import App, Image, asgi_app


def extract_code(reply):
    pattern = r"```python([\s\S]*?)```"
    matches = re.findall(pattern, reply)
    return "\n\n".join(matches)


PYTHON_AGENT_SYSTEM_PROMPT = """
You will write the solution and the test cases to a Leetcode problem.

Implement your code as a method in the `class Solution` along with the given test cases. The user will provide the output executed by the code.

When there are issues, following these steps
- Hand-calculate what the intermediate values should be
- Print the intermediate values in the code.

If the intermediate values are already printed
- Hand calculate what the intermediate values should be
- Analyze what is wrong with the intermediate values
- Fix the issue by implementing the full solution along with the given test cases, with the intermediate values printed

If you are repeatedly stuck on the same error, start afresh and try an entirely different method instead.

When a test case is given, hand-calculate the expected output first before writing code.

If the output looks ok, meticulously calculate the complexity of the solution to check whether it is within the time limit. (Note: "105" is likely 10**5).
Fix the code if it is likely to exceed time limit. Do not stop at a solution that will exceed the time limit.

class Solution:
    def ...

s = Solution()
print(s.<function>(<inputs>))  # Expected: <expected output>
print(s.<function>(<inputs>))  # Expected: <expected output>

Reminder:
- Write test cases in this format. Do not create new test cases, only use the given test cases.
- Always return the full solution and the test cases in the same Python block
""".strip()


CODE_WITH_WRAPPERS = """\
import math
from typing import *
from collections import *
import collections
import itertools

{code}
"""


SIMULATED_USER_REPLY_NO_OUTPUT_OR_ERROR = """\
There was code but there is no output.

Please write both the solution and the test cases.
"""

SIMULATED_USER_REPLY_OUTPUT_ONLY = """\
```output
{output}
```

Check whether the answers returned are expected.

If there are issues, hand calculate the intermediate values and print the intermediate values.

If the intermediate values are already printed, hand-calculate the intermediate values and compare with the printed values. Do not just analyze the output.

If all the answers are expected, check the time complexity.

Never stop at a solution that will exceed the time limit.
"""

SIMULATED_USER_SUFFIX_PROMPT = ""

SIMULATED_USER_REPLY_OUTPUT_AND_ERROR = """\
Your code was executed and this is the output and error.
```output
{output}
```

```error
{error}
```
"""

SIMULATED_USER_REPLY_ERROR_ONLY = """\
Your code was executed and this is the error.
```error
{error}
```
"""

# OPTIONS_STRING = """

# Options:

# Continue
# Optimize the solution.
# Create a large test case (do not check correctness for this large test case).
# Create a small test, hand-calculate its output, and compare the solution's output.
# Clean up the print statements.
# """.rstrip()


app = App("PythonAgent")


def wrap_code(code):
    # the wrapper code
    # - load session with dill (for the same conversation)
    # - execute the code
    # - save to image.png on plt.plot() and plt.show()
    # - save session with dill (if execution is successful)

    return CODE_WITH_WRAPPERS.format(code=code)


class PythonAgentBot(PoeBot):
    prompt_bot = "Claude-3.5-Sonnet-200k"
    code_iteration_limit = 10
    logit_bias = {}  # "!["
    allow_attachments = True
    system_prompt_role = "system"  # Claude-3 does not allow system prompt yet
    stateful = True

    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        last_message = request.query[-1].content
        original_message_id = request.message_id
        print("user_message")
        print(last_message)

        PYTHON_AGENT_SYSTEM_MESSAGE = ProtocolMessage(
            role=self.system_prompt_role, content=PYTHON_AGENT_SYSTEM_PROMPT
        )

        # otherwise, disable suggested replies
        yield fp.MetaResponse(
            text="",
            content_type="text/markdown",
            linkify=False,
            refetch_settings=False,
            suggested_replies=False,
        )

        request.query = [PYTHON_AGENT_SYSTEM_MESSAGE] + request.query
        request.logit_bias = self.logit_bias
        request.temperature = 0.1  # does this work?

        for query in request.query:
            query.message_id = ""

        for query in request.query:
            for attachment in query.attachments:
                query.content += f"\n\nThe user has provided {attachment.name} in the current directory."

        # for query in request.query:
        # bot calling doesn't allow attachments
        # query.attachments = []

        for code_iteration_count in range(self.code_iteration_limit - 1):
            print("code_iteration_count", code_iteration_count)

            # print(request)

            current_bot_reply = ""
            async for msg in stream_request(request, self.prompt_bot, request.api_key):
                if isinstance(msg, MetaMessage):
                    continue
                elif msg.is_suggested_reply:
                    yield self.suggested_reply_event(msg.text)
                elif msg.is_replace_response:
                    yield self.replace_response_event(msg.text)
                else:
                    current_bot_reply += msg.text
                    yield self.text_event(msg.text)
                    if extract_code(current_bot_reply):
                        # break when a Python code block is detected
                        yield self.text_event("\n")
                        break

            message = ProtocolMessage(role="bot", content=current_bot_reply)
            request.query.append(message)

            # if the bot output does not have code, terminate
            code = extract_code(current_bot_reply)
            if not code:
                break
            code = wrap_code(code)

            # prepare code for execution
            print("code")
            print(code)
            output = ""
            error = ""
            try:
                f = modal.Function.lookup("run-python-code-shared", "execute_code")
                output = f.remote(code)  # need async await?
            except modal.exception.TimeoutError:
                error = "Time limit exceeded."

            print("len(output)", len(output))
            print("len(error)", len(error))
            if error:  # for monitoring
                print("error")
                print(error)

            current_user_simulated_reply = ""
            file_url = ""
            if output and error:
                yield PartialResponse(
                    text=textwrap.dedent(f"\n\n```output\n{output}```\n\n")
                )
                yield PartialResponse(
                    text=textwrap.dedent(f"\n\n```error\n{error}```\n\n")
                )
                current_user_simulated_reply = (
                    SIMULATED_USER_REPLY_OUTPUT_AND_ERROR.format(
                        output=output, error=error
                    )
                )
            elif output:
                yield PartialResponse(
                    text=textwrap.dedent(f"\n\n```output\n{output}```\n\n")
                )
                current_user_simulated_reply = SIMULATED_USER_REPLY_OUTPUT_ONLY.format(
                    output=output
                )
            elif error:
                yield PartialResponse(
                    text=textwrap.dedent(f"\n\n```error\n{error}```\n\n")
                )
                current_user_simulated_reply = SIMULATED_USER_REPLY_ERROR_ONLY.format(
                    error=error
                )
            else:
                current_user_simulated_reply = SIMULATED_USER_REPLY_NO_OUTPUT_OR_ERROR

            current_user_simulated_reply += SIMULATED_USER_SUFFIX_PROMPT

            message = ProtocolMessage(role="user", content=current_user_simulated_reply)
            if file_url:
                message.attachments = [
                    Attachment(content_type="image/png", url=file_url, name="image.png")
                ]
            request.query.append(message)

        yield PartialResponse(text="Continue", is_suggested_reply=True)
        yield PartialResponse(text="Optimize the solution.", is_suggested_reply=True)
        yield PartialResponse(text="Create a large test case (do not check correctness for this large test case).", is_suggested_reply=True)
        yield PartialResponse(text="Create a small test, hand-calculate its output, and compare the solution's output.", is_suggested_reply=True)
        yield PartialResponse(text="Clean up the print statements.", is_suggested_reply=True)


    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={self.prompt_bot: self.code_iteration_limit},
            allow_attachments=self.allow_attachments,
            introduction_message="",
            enable_image_comprehension=True,
        )


image_bot = (
    Image.debian_slim()
    .pip_install("fastapi-poe==0.0.43", "requests==2.28.2", "cloudinary")
    .env(
        {
            "POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"],
            "CLOUDINARY_CLOUD_NAME": os.environ["CLOUDINARY_CLOUD_NAME"],
            "CLOUDINARY_API_KEY": os.environ["CLOUDINARY_API_KEY"],
            "CLOUDINARY_API_SECRET": os.environ["CLOUDINARY_API_SECRET"],
        }
    )
)

image_exec = Image.debian_slim().pip_install(
    "fastapi-poe==0.0.23",
    "huggingface-hub==0.16.4",
    "ipython",
    "scipy",
    "matplotlib",
    "scikit-learn",
    "pandas==1.3.2",
    "ortools",
    "torch",
    "torchvision",
    "tensorflow",
    "spacy",
    "transformers",
    "opencv-python-headless",
    "nltk",
    "openai",
    "requests",
    "beautifulsoup4",
    "newspaper3k",
    "feedparser",
    "sympy",
    "tensorflow",
    "cartopy",
    "wordcloud",
    "gensim",
    "keras",
    "librosa",
    "XlsxWriter",
    "docx2txt",
    "markdownify",
    "pdfminer.six",
    "Pillow",
    "opencv-python",
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
)


bot = PythonAgentBot()


@app.function(image=image_bot, container_idle_timeout=1200)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
