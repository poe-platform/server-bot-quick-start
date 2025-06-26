"""

BOT_NAME="CmdLine"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
echo z > a.txt
cat a.txt

"""

from __future__ import annotations

import os
import re
import stat
from typing import AsyncIterable

import fastapi_poe as fp
import modal
from fastapi_poe import PoeBot, make_app
from fastapi_poe.types import PartialResponse, QueryRequest, SettingsResponse, SettingsRequest
from modal import App, Image, asgi_app, Sandbox


def extract_codes(reply):
    pattern = r"```(?:bash|sh)\n([\s\S]*?)\n```"
    matches = re.findall(pattern, reply)
    if matches:
        return matches
    return []


image_exec = Image.debian_slim().apt_install("curl", "git", "ripgrep")

INTRODUCTION_MESSAGE = """This bot will execute bash commands.

````
```bash
pwd
```
````

Try copying the above, paste it, and reply."""

class CmdLineBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        for query in request.query[::-1]:
            commands = extract_codes(query.content)
            if commands:
                break
        else:
            commands = [request.query[-1].content]

        yield fp.MetaResponse(
            text="",
            content_type="text/markdown",
            linkify=True,
            refetch_settings=False,
            suggested_replies=False,
        )

        print("check")
        print(commands)

        for command in commands:
            nfs = modal.NetworkFileSystem.from_name(
                f"vol-{hash(request.user_id)}", create_if_missing=True
            )

            sb = Sandbox.create(
                "bash",
                "-c",
                f"cd /cache && {command}",
                image=image_exec,
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

            nothing_returned = True

            if output:
                yield PartialResponse(text=f"""```output\n{output}\n```\n""")
                nothing_returned = False
            if output and error:
                yield PartialResponse(text="""\n\n""")
            if error:
                yield PartialResponse(text=f"""```error\n{error}\n```\n""")
                nothing_returned = False

            if nothing_returned:
                yield PartialResponse(text="""No output or error returned.""")

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={},
            allow_attachments=False,  # to update when ready
            introduction_message=INTRODUCTION_MESSAGE,
        )
