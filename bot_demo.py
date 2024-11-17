# TODO - write script to update settings

"""
modal deploy bot_demo.py

modal app stop demo-bot-poe && modal deploy bot_demo.py
"""

from __future__ import annotations
import os

import fastapi_poe as fp
from modal import App, Image, Mount, asgi_app

from wrapper_bot import WrapperBot
from catbot import CatBot
from echobot import EchoBot
from function_calling_bot import GPT35FunctionCallingBot
from log_bot_copy import LogBot
from pdf_counter_bot import PDFSizeBot
from turbo_vs_claude import GPT35TurbovsClaudeBot
from image_response_bot import SampleImageResponseBot
from http_request_bot import HttpRequestBot
from prompt_bot import PromptBot
from turbo_allcapsbot import GPT35TurboAllCapsBot
from video_bot import VideoBot

REQUIREMENTS = [
    "fastapi-poe==0.0.48", 
    "devtools==0.12.2",
    "PyPDF2==3.0.1",
    "requests==2.31.0",
    "openai",
]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .env(
        {
            "POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"],
            "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
        }
    )
)
app = App(
    "demo-bot-poe",
    mounts=[Mount.from_local_dir("./assets", remote_path="/root/assets")],
)


@app.function(image=image, container_idle_timeout=1200)
@asgi_app()
def fastapi_app():
    POE_ACCESS_KEY = os.environ["POE_ACCESS_KEY"]
    # see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
    # app = fp.make_app(bot, access_key=POE_ACCESS_KEY, bot_name=<YOUR_BOT_NAME>)
    app = fp.make_app(
        [
            EchoBot(path="/EchoBotDemo", access_key=POE_ACCESS_KEY, bot_name="EchoBotDemo"),
            PromptBot(path="/PromptBotDemo", access_key=POE_ACCESS_KEY, bot_name="PromptBotDemo"),
            WrapperBot(path="/WrapperBotDemo", access_key=POE_ACCESS_KEY, bot_name="WrapperBotDemo"),
            CatBot(path="/CatBotDemo", access_key=POE_ACCESS_KEY, bot_name="CatBotDemo"),
            SampleImageResponseBot(path="/ImageResponseBotDemo", access_key=POE_ACCESS_KEY, bot_name="ImageResponseBotDemo"),
            VideoBot(path="/VideoBotDemo", access_key=POE_ACCESS_KEY, bot_name="VideoBotDemo"),
            PDFSizeBot(path="/PDFCounterBotDemo", access_key=POE_ACCESS_KEY, bot_name="PDFCounterBotDemo"),
            GPT35FunctionCallingBot(path="/FunctionCallingDemo", access_key=POE_ACCESS_KEY, bot_name="FunctionCallingDemo"),
            LogBot(path="/LogBotDemo", access_key=POE_ACCESS_KEY, bot_name="LogBotDemo"),
            HttpRequestBot(path="/HTTPRequestBotDemo", access_key=POE_ACCESS_KEY, bot_name="HTTPRequestBotDemo"),
            GPT35TurboAllCapsBot(path="/AllCapsBotDemo", access_key=POE_ACCESS_KEY, bot_name="AllCapsBotDemo"),
            GPT35TurbovsClaudeBot(path="/TurboVsClaudeBotDemo", access_key=POE_ACCESS_KEY, bot_name="TurboVsClaudeBotDemo"),
        ],
    )
    return app
