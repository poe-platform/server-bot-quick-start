"""

BOT_NAME="TrinoAgent"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
How to NVL

"""

import os
import re
import textwrap
from typing import AsyncIterable

import trino
from fastapi_poe import PoeBot, make_app
from fastapi_poe.client import MetaMessage, ProtocolMessage, stream_request
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import Image, Stub, asgi_app
from sse_starlette.sse import ServerSentEvent
from trino.exceptions import TrinoUserError

SYSTEM_PROMPT = """
You are an assistant that helps to write Trino queries.

Do NOT use semicolons.
Limit your results to at most 10 rows.
Capitalize all Trino keywords.

Always show an example by creating tables with some data

```sql
WITH (insert table name here) (insert comma-separated column names here) AS (
    -- define the table data here
)
SELECT
-- define the query logic here
LIMIT 10
```

Remember to name the columns.
Enclose the Trino queries with ```sql and ```
""".strip()


SIMULATED_USER_SUFFIX_PROMPT = """
Your query has produced the following output

<output>
{output}
</output>

If there is an issue, you will fix the Trino query.
Otherwise, provide a concise comment. Do not repeat the output. Do not mention that that is no issues.
""".strip()


def format_output(columns, rows) -> str:
    output = " | " + "|".join(column.name for column in columns) + " | "
    output += "\n" + " | " + " | ".join("-" for _ in columns) + " | "
    for row in rows:
        output += "\n" + " | " + " | ".join(str(value) for value in row) + " | "
    return output


def extract_code(reply):
    pattern = r"```sql([\s\S]*?)```"
    matches = re.findall(pattern, reply)
    return "\n\n".join(matches)


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
        return "```error\n" + e.error_name + "\n" + e.message + "\n```"
    rows = cur.fetchall()
    columns = cur.description
    output = format_output(columns, rows)
    return output


class TrinoAgentBot(PoeBot):
    prompt_bot = "ChatGPT"
    iteration_count = 3

    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[ServerSentEvent]:
        request.query = [
            ProtocolMessage(role="system", content=SYSTEM_PROMPT)
        ] + request.query

        request.logit_bias = {
            "17725": -20,  # (column
            "20184": -20,  # (col
            "49430": -20,  # (expression
            "26": -20,  # ;
            "280": -20,  # ;\n
            "45771": 10,  # WITH
            "3330": -10,  # ' column'
            "2007": -10,  # ' table'
            "366": -10,  # ' <'
            "1198": -10,  # ' --'
            "48014": -10,  # ' ...)'
        }
        user_statement = request.query[-1].content
        print("user_statement")
        print(user_statement)

        for _ in range(10):  # intentionally error if exceed limits
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
                        break

            query = extract_code(current_bot_reply)
            print("query")
            print(query)
            if not query:
                return

            yield self.text_event("\n\n\n")

            output = make_query(query)
            print("output")
            print(output)
            yield self.text_event(output)

            yield self.text_event("\n\n\n")

            request.query += [
                ProtocolMessage(role="bot", content=current_bot_reply),
                ProtocolMessage(
                    role="user",
                    content=SIMULATED_USER_SUFFIX_PROMPT.format(output=output),
                ),
            ]
            print(SIMULATED_USER_SUFFIX_PROMPT.format(output=output))

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(
            server_bot_dependencies={self.prompt_bot: self.iteration_count},
            allow_attachments=False,
            introduction_message=textwrap.dedent(
                """Which SQL keyword do you want to learn about?"""
            ).strip(),
        )


bot = TrinoAgentBot()

image_bot = (
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


@stub.function(image=image_bot)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
