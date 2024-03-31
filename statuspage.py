"""

modal deploy --name statuspage statuspage.py

"""

import asyncio
import os
import time
from datetime import datetime

import fastapi_poe.client as fp_client
import fastapi_poe.types as fp_types
import modal
import requests
from modal import Image, Stub

RETRY_COUNT = 2
DELAY_SECONDS = 10


async def get_bot_response(bot_name, messages):
    response = ""
    async for partial in fp_client.get_bot_response(
        messages=messages, bot_name=bot_name, api_key=os.environ["POE_API_KEY"]
    ):
        response += partial.text
    return response


def get_utc_timestring():
    current_utc_time = datetime.utcnow()
    formatted_time = current_utc_time.strftime("%Y-%m-%d %H:%M:%S")

    return formatted_time


def get_components():
    page_id = os.environ["STATUSPAGE_PAGE_ID"]
    api_key = os.environ["STATUSPAGE_API_KEY"]
    url = f"https://api.statuspage.io/v1/pages/{page_id}/components/"

    headers = {"Authorization": f"OAuth {api_key}"}

    response = requests.get(url, headers=headers)

    return response


def update_component(component_id, description, status):
    page_id = os.environ["STATUSPAGE_PAGE_ID"]
    api_key = os.environ["STATUSPAGE_API_KEY"]
    url = f"https://api.statuspage.io/v1/pages/{page_id}/components/{component_id}"

    headers = {"Authorization": f"OAuth {api_key}", "Content-Type": "application/json"}

    payload = {"component": {"description": description, "status": status}}

    response = requests.patch(url, headers=headers, json=payload)

    return response


def test_bot(
    bot_name, user_message, expected_reply_substring, bot_name_to_compoenent_id
):
    component_id = bot_name_to_compoenent_id[bot_name]

    print(f"Testing {bot_name}")

    messages = [fp_types.ProtocolMessage(role="user", content=user_message)]
    response = None

    for _ in range(RETRY_COUNT):
        try:
            response = asyncio.run(get_bot_response(bot_name, messages))
            print(f"Response:\n{response}")
        except Exception as e:
            print(str(e))

        if response is None:
            description = f"Did not receive response at {get_utc_timestring()} UTC"
            status = "major_outage"

        elif expected_reply_substring in response:
            description = f"Expected response received at {get_utc_timestring()} UTC"
            status = "operational"

        else:
            description = f"Response did not contain expected substring at {get_utc_timestring()} UTC"
            status = "degraded_performance"

        print(f"Description: {description}")
        print(f"Status: {status}")
        print()

        update_component(component_id, description, status)

        if status == "operational":
            break

        time.sleep(DELAY_SECONDS)


image = (
    Image.debian_slim()
    .pip_install("requests", "fastapi-poe")
    .env(
        {
            "STATUSPAGE_PAGE_ID": os.environ["STATUSPAGE_PAGE_ID"],
            "STATUSPAGE_API_KEY": os.environ["STATUSPAGE_API_KEY"],
            "POE_API_KEY": os.environ["POE_API_KEY"],
        }
    )
)

stub = Stub()


@stub.function(image=image, schedule=modal.Period(minutes=1))
def update_statuspage_minutely():
    BOT_NAME_TO_COMPONENT_ID = {}
    for component in get_components().json():
        BOT_NAME_TO_COMPONENT_ID[component["name"]] = component["id"]

    test_bot(
        bot_name="EchoBotDemonstration",
        user_message="hello there",
        expected_reply_substring="hello there",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )

    test_bot(
        bot_name="Solar-Mini",
        user_message="What is 1+2?",
        expected_reply_substring="3",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )


@stub.function(image=image, schedule=modal.Period(minutes=10))
def update_statuspage_ten_minutely():
    BOT_NAME_TO_COMPONENT_ID = {}
    for component in get_components().json():
        BOT_NAME_TO_COMPONENT_ID[component["name"]] = component["id"]

    test_bot(
        bot_name="ChatGPT",
        user_message="What is 1+2?",
        expected_reply_substring="3",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )

    test_bot(
        bot_name="Claude-instant",
        user_message="What is 1+2?",
        expected_reply_substring="3",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )

    test_bot(
        bot_name="Llama-2-70b",
        user_message="What is 1+2?",
        expected_reply_substring="3",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )

    test_bot(
        bot_name="Mixtral-8x7B-Chat",
        user_message="What is 1+2?",
        expected_reply_substring="3",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )

    test_bot(
        bot_name="AllCapsBotDemo",
        user_message="Who is the 1st US President?",
        expected_reply_substring="WASHINGTON",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )

    test_bot(
        bot_name="FunctionCallingDemo",
        user_message="What is the temperate in Tokyo?",
        expected_reply_substring="11",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )

    test_bot(
        bot_name="PythonAgent",
        user_message="Calculate 3 to the power of 1009 modulo 65537",
        expected_reply_substring="32057",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )

    # currently there is issues with testing attachment responses
    # test_bot(
    #     bot_name="PythonAgent",
    #     user_message="make scatter plot",
    #     expected_reply_substring="![plot]",
    #     bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    # )


@stub.function(image=image, schedule=modal.Period(hours=1))
def update_statuspage_hourly():
    BOT_NAME_TO_COMPONENT_ID = {}
    for component in get_components().json():
        BOT_NAME_TO_COMPONENT_ID[component["name"]] = component["id"]

    test_bot(
        bot_name="H-1B",
        user_message="Count the number H-1B1 Singapore applications in 2022",
        expected_reply_substring="1467",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )

    test_bot(
        bot_name="TrinoAgent",
        user_message="How do I use array function CONTAINS",
        expected_reply_substring="|",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )


@stub.function(image=image, schedule=modal.Period(days=1))
def update_statuspage_daily():
    BOT_NAME_TO_COMPONENT_ID = {}
    for component in get_components().json():
        BOT_NAME_TO_COMPONENT_ID[component["name"]] = component["id"]

    test_bot(
        bot_name="CafeMaid",
        user_message="I want coffee",
        expected_reply_substring="![",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )

    test_bot(
        bot_name="GPT-4-128k-mirror",
        user_message="What is 1+2",
        expected_reply_substring="3",
        bot_name_to_compoenent_id=BOT_NAME_TO_COMPONENT_ID,
    )


# attachments is not working when sent through Poe API
# this is for poe.com/ResumeReview
message = fp_types.ProtocolMessage(
    role="user",
    content="Review this",
    attachments=[
        fp_types.Attachment(
            url="https://resume.huikang.dev/media/resume.pdf",
            content_type="application/pdf",
            name="resume.pdf",
        )
    ],
)
