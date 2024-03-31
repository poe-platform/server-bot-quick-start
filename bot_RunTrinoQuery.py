"""

BOT_NAME="RunTrinoQuery"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
SELECT nationkey, name FROM tpch.sf1.nation

"""

import os
import textwrap
from typing import AsyncIterable

import trino
from fastapi_poe import PoeBot, make_app
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import Image, Stub, asgi_app
from sse_starlette.sse import ServerSentEvent
from trino.exceptions import TrinoUserError


def format_output(columns, rows) -> str:
    output = " | " + "|".join(column.name for column in columns) + " | "
    output += "\n" + " | " + " | ".join("-" for _ in columns) + " | "
    for row in rows:
        output += "\n" + " | " + " | ".join(str(value) for value in row) + " | "
    return output


def strip_code(code):
    if len(code.strip()) < 6:
        return code
    code = code.strip()
    if code.startswith("```") and code.endswith("```"):
        code = code[3:-3]
    return code


conn = trino.dbapi.connect(
    host=os.environ["TRINO_HOST_URL"],
    port=443,
    http_scheme="https",
    auth=trino.auth.BasicAuthentication(
        os.environ["TRINO_USERNAME"], os.environ["TRINO_PASSWORD"]
    ),
)
cur = conn.cursor()


def make_query(query):
    try:
        cur.execute(query)
    except TrinoUserError as e:
        return "```python\n" + str(e) + "\n```"
    rows = cur.fetchall()
    columns = cur.description
    output = format_output(columns, rows)
    return output


class EchoBot(PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[ServerSentEvent]:
        user_statement = request.query[-1].content
        print("user_statement")
        print(user_statement)
        user_statement = strip_code(user_statement)
        output = make_query(user_statement)
        yield self.text_event(output)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={},
            allow_attachments=False,
            introduction_message=textwrap.dedent(
                """
            Please send a Trino query, such as
            ```
            SELECT nationkey, name FROM tpch.sf1.nation
            ```
            """
            ).strip(),
        )


bot = EchoBot()

image = (
    Image.debian_slim()
    .pip_install("fastapi-poe==0.0.23", "trino")
    .env(
        {
            "POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"],
            "TRINO_HOST_URL": os.environ["TRINO_HOST_URL"],
            "TRINO_USERNAME": os.environ["TRINO_USERNAME"],
            "TRINO_PASSWORD": os.environ["TRINO_PASSWORD"],
        }
    )
)

stub = Stub("poe-bot-quickstart")


@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
