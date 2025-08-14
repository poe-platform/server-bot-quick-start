import json
import os
from typing import AsyncIterable

import fastapi_poe as fp
import requests
from modal import App, Image, asgi_app

# TODO: set your bot access key and bot name for this bot to work
# see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
bot_access_key = os.getenv("POE_ACCESS_KEY")
bot_name = ""

TOOL_CALL_BOT = "GPT-4o"
MAX_BOT_CALLS = 10


# Define a list of callable tools for the model
def get_weather(latitude: float, longitude: float) -> float:
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}"
        "&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,"
        "relative_humidity_2m,wind_speed_10m"
    )
    data = response.json()
    return data["current"]["temperature_2m"]


tools_dicts = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current temperature for provided coordinates in celsius.",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
                "required": ["latitude", "longitude"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
]
tool_executables_map = {"get_weather": get_weather}
tool_definitions = [fp.ToolDefinition(**tools_dict) for tools_dict in tools_dicts]


def get_tool_call_result(tool_call: fp.ToolCallDefinition) -> fp.ToolResultDefinition:
    """Execute the tool and return the result wrapped in a ToolResultDefinition"""
    tool_name = tool_call.function.name
    tool_args = json.loads(tool_call.function.arguments)
    tool_function = tool_executables_map[tool_name]

    result = tool_function(**tool_args)
    return fp.ToolResultDefinition(
        role="tool", name=tool_name, tool_call_id=tool_call.id, content=str(result)
    )


class FunctionCallingLoopBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        # Load the tool messages from the previous calls to this server bot
        chat_context_with_metadata_expanded: list[fp.ProtocolMessage] = []
        for msg in request.query:
            if msg.metadata is not None:
                metadata_message_dicts = json.loads(msg.metadata)
                chat_context_with_metadata_expanded.extend(
                    [
                        fp.ProtocolMessage.model_validate(metadata_message_dict)
                        for metadata_message_dict in metadata_message_dicts
                    ]
                )
            chat_context_with_metadata_expanded.append(
                msg.model_copy(update={"metadata": None})
            )
        request.query = chat_context_with_metadata_expanded
        tool_messages: list[fp.ProtocolMessage] = []

        continue_tool_loop = True
        call_count = 0
        while continue_tool_loop:
            continue_tool_loop = False
            tool_calls: dict[int, fp.ToolCallDefinition] = {}
            call_count += 1

            # Make sure to produce a final response if no more bot calls are allowed.
            force_final_response = call_count >= MAX_BOT_CALLS

            # 1. [First iteration] Make a request to the model with tools it could call
            # 4. [Subsequent iterations] Make another request to the model with the tool output
            async for msg in fp.stream_request(
                request,
                TOOL_CALL_BOT,
                request.access_key,
                tools=None if force_final_response else tool_definitions,
            ):
                # 2. [First iteration] Receive a tool call from the model
                # 5. [Subsequent iterations] Receive a final response from the model (or more
                # tool calls)
                if msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        if tool_call.index not in tool_calls:
                            tool_calls[tool_call.index] = tool_call
                        else:
                            tool_calls[
                                tool_call.index
                            ].function.arguments += tool_call.function.arguments
                    continue_tool_loop = True

                else:
                    yield msg

            tool_results: list[fp.ToolResultDefinition] = []
            for tool_call in tool_calls.values():
                # 3. Execute code on the application side with input from the tool call
                tool_result = get_tool_call_result(tool_call)
                tool_results.append(tool_result)

            # Add the tool calls and results to the context for subsequent requests to the model
            if tool_calls and tool_results:
                tool_call_message = fp.ProtocolMessage(
                    role="bot",
                    message_type="function_call",
                    content=json.dumps(
                        [tool_call.model_dump() for tool_call in tool_calls.values()]
                    ),
                )
                request.query.append(tool_call_message)
                tool_messages.append(tool_call_message)

                tool_result_message = fp.ProtocolMessage(
                    role="tool",
                    content=json.dumps(
                        [tool_result.model_dump() for tool_result in tool_results]
                    ),
                )
                request.query.append(tool_result_message)
                tool_messages.append(tool_result_message)

        # Store the tool messages for later calls to this server bot
        yield fp.DataResponse(
            metadata=json.dumps(
                [tool_message.model_dump() for tool_message in tool_messages]
            )
        )

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies={TOOL_CALL_BOT: MAX_BOT_CALLS}
        )


REQUIREMENTS = ["fastapi-poe==0.0.68", "requests"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .env({"POE_ACCESS_KEY": bot_access_key})
)
app = App("function-calling-loop-bot")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = FunctionCallingLoopBot()
    app = fp.make_app(
        bot,
        access_key=bot_access_key,
        bot_name=bot_name,
        allow_without_key=not (bot_access_key and bot_name),
    )
    return app
