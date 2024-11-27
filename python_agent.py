"""

BOT_NAME="PythonAgent";
modal deploy --name $BOT_NAME bot_${BOT_NAME}.py;
curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

"""

from __future__ import annotations

import re
import textwrap
from typing import AsyncIterable

import modal
import requests
from fastapi_poe import PoeBot
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import (
    PartialResponse,
    ProtocolMessage,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
from modal import Image, Sandbox

PYTHON_AGENT_SYSTEM_PROMPT = """
You write the Python code for me

When you return Python code
- Encapsulate all Python code within triple backticks (i.e ```python) with newlines.
- The Python code should either print something or plot something
- The Python code should not use input()

I have already installed these Python packages

numpy
scipy
matplotlib
basemap (in mpl_toolkits.basemap)
scikit-learn
pandas (prefer pandas over csv)
ortools
torch
torchvision
tensorflow
transformers
opencv-python-headless
nltk
openai
requests
beautifulsoup4
newspaper3k
feedparser
sympy
yfinance
"""

# probably there is a better method to retain memory than to pickle
CODE_WITH_WRAPPERS = """\
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import savefig

def save_image(filename):
    def decorator(func):
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            savefig(filename)
        return wrapper
    return decorator

plt.show = save_image('image.png')(plt.show)
plt.savefig = save_image('image.png')(plt.savefig)

import dill, os, pickle
if os.path.exists("{conversation_id}.dill"):
    try:
        with open("{conversation_id}.dill", 'rb') as f:
            dill.load_session(f)
    except:
        pass

{code}

try:
    with open('{conversation_id}.dill', 'wb') as f:
        dill.dump_session(f)
except:
    pass
"""

SIMULATED_USER_REPLY_OUTPUT_ONLY = """\
Your code was executed and this is the output.
```output
{output}
```
"""

SIMULATED_USER_REPLY_ERROR_ONLY = """\
Your code was executed and this is the error.
```error
{error}
```
"""

SIMULATED_USER_REPLY_OUTPUT_AND_ERROR = """\
Your code was executed and this is the output and error.
```output
{output}
```

```error
{error}
```
"""

SIMULATED_USER_REPLY_NO_OUTPUT_OR_ERROR = """\
Your code was executed without issues, without any standard output.
"""

SIMULATED_USER_SUFFIX_IMAGE_FOUND = """

Your code was executed and it displayed a plot as attached.
Please describe the plot and check if it makes sense.
"""

SIMULATED_USER_SUFFIX_IMAGE_NOT_FOUND = """

Your code was executed but it did not display a plot.
"""

SIMULATED_USER_SUFFIX_PROMPT = """
If there is an issue, you will fix the Python code.

Otherwise, conclude with only text in plaintext. Do NOT produce the final version of the script.
"""


IMAGE_EXEC = (
    Image.debian_slim()
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
    )
)


class PythonAgentBot(PoeBot):
    prompt_bot = "GPT-4o"
    code_iteration_limit = 3
    logit_bias = {}  # "!["
    allow_attachments = True
    system_prompt_role: str | None = (
        "system"  # Claude-3 does not allow system prompt yet
    )
    python_agent_system_prompt: str | None = PYTHON_AGENT_SYSTEM_PROMPT
    code_with_wrappers = CODE_WITH_WRAPPERS
    simulated_user_suffix_prompt = SIMULATED_USER_SUFFIX_PROMPT
    image_exec = IMAGE_EXEC

    def extract_code(self, text):
        pattern = r"\n```python([\s\S]*?)\n```"
        matches = re.findall(pattern, "\n" + text)
        if matches:
            return "\n\n".join(matches)

        pattern = r"```python([\s\S]*?)```"
        matches = re.findall(pattern, "\n" + text)
        return "\n\n".join(textwrap.dedent(match) for match in matches)

    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        last_message = request.query[-1].content
        original_message_id = request.message_id
        print("user_message")
        print(last_message)

        assert (self.python_agent_system_prompt is not None) == (
            self.system_prompt_role is not None
        )
        if self.python_agent_system_prompt is not None:
            PYTHON_AGENT_SYSTEM_MESSAGE = ProtocolMessage(
                role=self.system_prompt_role, content=self.python_agent_system_prompt
            )
            request.query = [PYTHON_AGENT_SYSTEM_MESSAGE] + request.query

        request.logit_bias = self.logit_bias
        request.temperature = 0.1  # does this work?

        for query in request.query:
            query.message_id = ""

        nfs = modal.NetworkFileSystem.from_name(
            f"vol-{request.user_id[::-1][:32][::-1]}", create_if_missing=True
        )

        for query in request.query:
            for attachment in query.attachments:
                query.content += f"\n\nThe user has provided {attachment.name} in the current directory."

        # upload files in latest user message
        for attachment in request.query[-1].attachments:
            r = requests.get(attachment.url)
            with open(attachment.name, "wb") as f:
                f.write(r.content)
            nfs.add_local_file(attachment.name, attachment.name)

        # for query in request.query:
        # bot calling doesn't allow attachments
        # query.attachments = []

        for code_iteration_count in range(self.code_iteration_limit - 1):
            print("code_iteration_count", code_iteration_count)

            print(request)

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
                    if self.extract_code(current_bot_reply):
                        # break when a Python code block is detected
                        break

            message = ProtocolMessage(role="bot", content=current_bot_reply)
            request.query.append(message)

            # if the bot output does not have code, terminate
            code = self.extract_code(current_bot_reply)
            if not code:
                return

            # prepare code for execution
            print("code")
            print(code)
            wrapped_code = self.code_with_wrappers.format(
                code=code, conversation_id=request.conversation_id
            )

            # upload python script
            with open(f"{request.conversation_id}.py", "w") as f:
                f.write(wrapped_code)
            nfs.add_local_file(
                f"{request.conversation_id}.py",
                f"{request.conversation_id[::-1][:32][::-1]}.py",
            )

            # execute code
            sb = Sandbox.create(
                "bash",
                "-c",
                f"cd /cache && python {request.conversation_id[::-1][:32][::-1]}.py",
                image=self.image_exec,
                network_file_systems={"/cache": nfs},
            )
            sb.wait()

            print("sb.returncode", sb.returncode)

            output = sb.stdout.read()
            error = sb.stderr.read()

            print("len(output)", len(output))
            print("len(error)", len(error))
            if error:  # for monitoring
                print("error")
                print(error)

            current_user_simulated_reply = ""
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

            # upload image and get image url
            image_data = None
            if any("image.png" in str(entry) for entry in nfs.listdir("*")):
                # some roundabout way to check if image file is in directory
                with open("image.png", "wb") as f:
                    for chunk in nfs.read_file("image.png"):
                        f.write(chunk)

                image_data = None
                with open("image.png", "rb") as f:
                    image_data = f.read()

                if image_data:
                    attachment_upload_response = await self.post_message_attachment(
                        message_id=original_message_id,
                        file_data=image_data,
                        filename="image.png",
                        is_inline=True,
                    )
                    print("inline_ref", attachment_upload_response.inline_ref)
                    yield PartialResponse(
                        text=f"\n\n![plot][{attachment_upload_response.inline_ref}]\n\n"
                    )
                    nfs.remove_file("image.png")

            yield self.text_event("\n")

            if image_data is not None:
                current_user_simulated_reply += SIMULATED_USER_SUFFIX_IMAGE_FOUND
            else:
                if "matplotlib" in code:
                    current_user_simulated_reply += (
                        SIMULATED_USER_SUFFIX_IMAGE_NOT_FOUND
                    )

            current_user_simulated_reply += self.simulated_user_suffix_prompt

            # TODO when feature allows, add image to ProtocolMessage
            message = ProtocolMessage(role="user", content=current_user_simulated_reply)
            request.query.append(message)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={self.prompt_bot: self.code_iteration_limit},
            allow_attachments=self.allow_attachments,
            introduction_message="",
            enable_image_comprehension=True,
        )


class PythonAgentExBot(PythonAgentBot):
    prompt_bot = "Claude-3.5-Sonnet-200k"
    code_iteration_limit = 5
    system_prompt_role = "system"


class LeetCodeAgentBot(PythonAgentBot):
    prompt_bot = "o1-mini"
    code_iteration_limit = 5
    system_prompt_role = "user"
    python_agent_system_prompt = textwrap.dedent(
        """
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
        """
    ).strip()
