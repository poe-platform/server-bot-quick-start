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
import textwrap
import uuid
from typing import AsyncIterable

from fastapi_poe import PoeBot, make_app
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


class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:
        last_message = request.query[-1].content
        random_uuid = uuid.uuid4()

        with open("puppeteer-config.json", "w") as f:
            f.write(puppeteer_config_json_content)

        with open(f"{random_uuid}.md", "w") as f:
            f.write(last_message)

        # svg is not supported
        command = f"mmdc -p puppeteer-config.json -i {random_uuid}.md -o {random_uuid}-output.png"
        _ = subprocess.check_output(command, shell=True, text=True)

        filenames = list(glob.glob(f"{random_uuid}-output-*.png"))

        if len(filenames) == 0:
            yield PartialResponse(
                text=textwrap.dedent(
                    """
                No mermaid diagrams were found in your previous message.

                A mermaid diagram will look like

                ```mermaid
                graph TD
                    A[Client] --> B[Load Balancer]
                ```

                See examples [here](https://docs.mermaidchart.com/mermaid/intro).
            """
                )
            )
            return

        for filename in filenames:
            print("filename", filename)
            with open(filename, "rb") as f:
                file_data = f.read()

            attachment_upload_response = await self.post_message_attachment(
                access_key=os.environ["POE_ACCESS_KEY"],
                message_id=request.message_id,
                file_data=file_data,
                filename=filename,
                is_inline=True,
            )
            yield PartialResponse(
                text=f"\n\n![flowchart][{attachment_upload_response.inline_ref}]\n\n"
            )

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            introduction_message="This bot will draw [mermaid diagrams](https://docs.mermaidchart.com/mermaid/intro)."
        )


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
    .pip_install("fastapi-poe==0.0.32")
    .env({"POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"]})
)

stub = Stub("poe-bot-quickstart")

bot = EchoBot()


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
