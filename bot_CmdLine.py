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
from fastapi_poe.types import PartialResponse, QueryRequest
from modal import App, Image, asgi_app


def extract_codes(reply):
    pattern = r"```(bash|sh)\n([\s\S]*?)\n```"
    matches = re.findall(pattern, reply)
    if matches:
        return matches
    return []


image_exec = Image.debian_slim().apt_install("curl").apt_install("git")


class EchoBot(PoeBot):
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
                f"vol-{request.user_id}", create_if_missing=True
            )

            filename = f"{request.conversation_id}.sh"
            with open(f"{filename}", "w") as f:
                f.write(command)
            os.chmod(filename, os.stat(filename).st_mode | stat.S_IEXEC)

            nfs.add_local_file(
                f"{request.conversation_id}.sh", f"{request.conversation_id}.sh"
            )

            sb = app.spawn_sandbox(
                "bash",
                "-c",
                f"cd /cache && {command}",
                # f"cd /cache && chmod +x {filename} && ./{filename}",
                network_file_systems={"/cache": nfs},
                image=image_exec,
            )
            sb.wait()

            output = sb.stdout.read()
            error = sb.stderr.read()

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


# specific to hosting with modal.com
image = (
    Image.debian_slim()
    .pip_install("fastapi-poe==0.0.45")
    .env({"POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"]})
)

app = App("poe-bot-quickstart")

bot = EchoBot()


@app.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
