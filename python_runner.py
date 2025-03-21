from __future__ import annotations

import os
import re
from typing import AsyncIterable

import fastapi_poe as fp
from modal import App, Image, asgi_app

# TODO: set your bot access key and bot name for full functionality
# see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
bot_access_key = os.getenv("POE_ACCESS_KEY")
bot_name = ""


def override_message(request: fp.QueryRequest, message: str):
    new_query = request.model_copy(
        update={"query": [fp.ProtocolMessage(role="user", content=message)]}
    )
    return new_query


class CodeGenAndRunnerBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        """
        1. Call Claude-3.5-Sonnet to generate code based on the user's request.
        2. Pass the returned code to the Python bot.
        3. If there's an error, call Claude-3.5-Sonnet again with the error message for debugging.
        4. Re-run the updated code on the Python bot.
        5. Return the final result (or last error if debugging failed).
        """

        user_message = request.query[-1].content.strip()
        if not user_message:
            yield fp.PartialResponse(
                text="Please provide a prompt describing the code you want generated."
            )
            return

        # -------------
        # 1) Ask Claude-3.5-Sonnet to generate code
        # -------------
        yield fp.PartialResponse(text="Generating code with Claude-3.5-Sonnet...\n")
        # We'll give it the user's message: user_message
        # Let’s define a prompt that instructs Claude to produce Python code:
        gen_code_prompt = (
            "You are a helpful coding assistant. The user wants some Python code. "
            "Please provide only the Python code (no markdown fences) needed to "
            "accomplish the following request:\n\n"
            f"{user_message}\n\n"
            "Do not include any comments or other text in the code. Do not offer to "
            "explain the code."
        )

        # Wrap the code in triple backticks for nice formatting
        yield fp.PartialResponse(text="```python\n")
        code_snippet = ""
        async for msg in fp.stream_request(
            override_message(request, gen_code_prompt),
            "Claude-3.5-Sonnet",
            request.access_key,
        ):
            if msg.text:
                code_snippet += msg.text
            yield fp.PartialResponse(text=msg.text)
        yield fp.PartialResponse(text="\n```")

        # Clean up code snippet by removing triple backticks
        # This is incase Claude ignored the instructions.
        code_snippet = re.sub(r"```+", "", code_snippet).strip()

        # -------------
        # 2) Run the code in the Python bot
        # -------------
        yield fp.PartialResponse(text="\nRunning the code in Python...\n")

        python_result = await fp.get_final_response(
            override_message(request, code_snippet), "Python", request.access_key
        )

        # Check if Python returned an error by looking for "Traceback" or "Error" keywords
        error_keywords = ["Traceback (most recent call last):", "Error:"]
        has_error = any(keyword in python_result for keyword in error_keywords)
        yield fp.PartialResponse(text=f"Output of code:\n{python_result}")

        # -------------
        # 3) If there's an error, call Claude to help debug
        # -------------
        if has_error:
            yield fp.PartialResponse(
                text="\nWe got an error when running the code. Asking "
                "Claude-3.5-Sonnet to debug...\n"
            )

            debug_prompt = (
                "The following Python code produced an error. "
                f"Original code:\n{code_snippet}\n\n"
                f"Error:\n{python_result}\n\n"
                "Please provide only the Python code (no markdown fences) needed to "
                "fix the error."
                " Do not include any comments or other text in the code. "
                "Do not offer to explain the code."
            )
            debug_code_snippet = ""
            yield fp.PartialResponse(text="```python\n")
            async for msg in fp.stream_request(
                override_message(request, debug_prompt),
                "Claude-3.5-Sonnet",
                request.access_key,
            ):
                if msg.text:
                    debug_code_snippet += msg.text
                yield fp.PartialResponse(text=msg.text)
            yield fp.PartialResponse(text="\n```")
            debug_code_snippet = re.sub(r"```+", "", debug_code_snippet).strip()

            yield fp.PartialResponse(
                text="\nRe-running the updated code in Python...\n"
            )

            python_debug_result = await fp.get_final_response(
                override_message(request, debug_code_snippet),
                "Python",
                request.access_key,
            )

            yield fp.PartialResponse(
                text=f"Output of debugged code:\n{python_debug_result}"
            )

            # If we still have error, just give up and display it
            if any(kw in python_debug_result for kw in error_keywords):
                yield fp.PartialResponse(
                    text=(
                        "It seems we have another error even after debugging:\n\n"
                        f"{python_debug_result}\n\n"
                        "You can try refining your request or debugging further."
                    )
                )
                return
            else:
                # Summarize successful run with Claude:
                yield fp.PartialResponse(
                    text="\nDebugged code ran successfully. Summarizing the final output...\n"
                )
                # We'll make a request to Claude-3.5-Sonnet to summarize the result:
                summary_prompt = (
                    "The original user request was:\n"
                    f"{user_message}\n\n"
                    "The code that was generated and run was:\n"
                    f"{code_snippet}\n\n"
                    "But we got an error. So we debugged it and ran the following code:\n"
                    f"{debug_code_snippet}\n\n"
                    "The output of the code was:\n"
                    f"{python_debug_result}\n\n"
                    "Please summarize the output of the code, and whether it fulfilled the "
                    "original request."
                )

                async for msg in fp.stream_request(
                    override_message(request, summary_prompt),
                    "Claude-3.5-Sonnet",
                    request.access_key,
                ):
                    yield fp.PartialResponse(text=msg.text)
                return
        else:
            # -------------
            # 4) If there's no error, summarize the result
            # -------------
            yield fp.PartialResponse(
                text="\nThe code ran successfully on the first try.\n"
            )
            yield fp.PartialResponse(
                text="Asking Claude-3.5-Sonnet for a brief summary of the output...\n"
            )
            summary_prompt = (
                "The original user request was:\n"
                f"{user_message}\n\n"
                "The code that was generated and run was:\n"
                f"{code_snippet}\n\n"
                "The output of the code was:\n"
                f"{python_result}\n\n"
                "Please summarize the output of the code, and whether it fulfilled the "
                "original request."
            )

            async for msg in fp.stream_request(
                override_message(request, summary_prompt),
                "Claude-3.5-Sonnet",
                request.access_key,
            ):
                yield fp.PartialResponse(text=msg.text)

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        """
        We declare dependencies for:
        - Claude-3.5-Sonnet (possibly: 3 calls in worst case).
        - Python (possibly: 2 or 3 calls in worst case).
        """
        return fp.SettingsResponse(
            server_bot_dependencies={"Claude-3.5-Sonnet": 3, "Python": 3}
        )


REQUIREMENTS = ["fastapi-poe"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .env({"POE_ACCESS_KEY": bot_access_key})
)
app = App("code-gen-and-runner-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = CodeGenAndRunnerBot()
    application = fp.make_app(
        bot,
        access_key=bot_access_key,
        bot_name=bot_name,
        allow_without_key=not (bot_access_key and bot_name),
    )
    return application
