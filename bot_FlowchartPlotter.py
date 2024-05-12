"""

BOT_NAME="FlowchartPlotter"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
echo z > a.txt
cat a.txt

"""

from __future__ import annotations

import glob
import os
import subprocess
import uuid
from typing import AsyncIterable

from fastapi_poe import MetaResponse, PoeBot, make_app
from fastapi_poe.types import (
    PartialResponse,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)
from modal import Image, Stub, asgi_app

puppeteer_config_json_content = """{
  "args": ["--no-sandbox"]
}
"""

INTRODUCTION_MESSAGE = """
This bot will draw [mermaid diagrams](https://docs.mermaidchart.com/mermaid/intro).

A mermaid diagram will look like this

````
```mermaid
graph TD
    A[Client] --> B[Load Balancer]
```
````

Try copying the above, paste it, and reply.
""".strip()


RESPONSE_MERMAID_DIAGRAM_MISSING = """
No mermaid diagrams were found in your previous message.

A mermaid diagram will look like

````
```mermaid
graph TD
    A[Client] --> B[Load Balancer]
```
````

See examples [here](https://docs.mermaidchart.com/mermaid/intro).
""".strip()


class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:

        # disable suggested replies
        yield MetaResponse(
            text="",
            content_type="text/markdown",
            linkify=True,
            refetch_settings=False,
            suggested_replies=False,
        )

        while request.query:
            last_message = request.query[-1].content
            print(last_message)
            if "```mermaid" in last_message:
                break
            request.query.pop()
            if len(request.query) == 0:
                yield PartialResponse(text=RESPONSE_MERMAID_DIAGRAM_MISSING)
                return

        random_uuid = uuid.uuid4()

        with open("puppeteer-config.json", "w") as f:
            f.write(puppeteer_config_json_content)

        with open(f"{random_uuid}.md", "w") as f:
            f.write(last_message)

        # svg is not supported
        command = f"mmdc -p puppeteer-config.json -i {random_uuid}.md -o {random_uuid}-output.png"
        yield PartialResponse(text="Drawing ...")

        _ = subprocess.check_output(command, shell=True, text=True)

        filenames = list(glob.glob(f"{random_uuid}-output-*.png"))

        if len(filenames) == 0:
            yield PartialResponse(
                text=RESPONSE_MERMAID_DIAGRAM_MISSING, is_replace_response=True
            )
            return

        for filename in filenames:
            print("filename", filename)
            with open(filename, "rb") as f:
                file_data = f.read()

            attachment_upload_response = await self.post_message_attachment(
                message_id=request.message_id,
                file_data=file_data,
                filename=filename,
                is_inline=True,
            )
            yield PartialResponse(
                text=f"\n\n![flowchart][{attachment_upload_response.inline_ref}]\n\n",
                is_replace_response=True,
            )

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(introduction_message=INTRODUCTION_MESSAGE)


# specific to hosting with modal.com
image = (
    Image.debian_slim()
    # puppeteer requirements
    .apt_install("ca-certificates")
    .apt_install("fonts-liberation")
    .apt_install("libasound2")
    .apt_install("libatk-bridge2.0-0")
    .apt_install("libatk1.0-0")
    .apt_install("libc6")
    .apt_install("libcairo2")
    .apt_install("libcups2")
    .apt_install("libdbus-1-3")
    .apt_install("libexpat1")
    .apt_install("libfontconfig1")
    .apt_install("libgbm1")
    .apt_install("libgcc1")
    .apt_install("libglib2.0-0")
    .apt_install("libgtk-3-0")
    .apt_install("libnspr4")
    .apt_install("libnss3")
    .apt_install("libpango-1.0-0")
    .apt_install("libpangocairo-1.0-0")
    .apt_install("libstdc++6")
    .apt_install("libx11-6")
    .apt_install("libx11-xcb1")
    .apt_install("libxcb1")
    .apt_install("libxcomposite1")
    .apt_install("libxcursor1")
    .apt_install("libxdamage1")
    .apt_install("libxext6")
    .apt_install("libxfixes3")
    .apt_install("libxi6")
    .apt_install("libxrandr2")
    .apt_install("libxrender1")
    .apt_install("libxss1")
    .apt_install("libxtst6")
    .apt_install("lsb-release")
    .apt_install("wget")
    .apt_install("xdg-utils")
    # mermaid requirements
    .apt_install("curl")
    .run_commands("curl -sL https://deb.nodesource.com/setup_18.x | bash -")
    .apt_install("nodejs")
    .run_commands("npm install -g @mermaid-js/mermaid-cli")
    # fastapi_poe requirements
    .pip_install("fastapi-poe==0.0.37")
    .env({"POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"]})
)

stub = Stub("poe-bot-FlowChartPlotter")

bot = EchoBot()


@stub.function(image=image, container_idle_timeout=1200)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
