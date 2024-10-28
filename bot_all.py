# TODO - write script to update settings

from __future__ import annotations
import os

import fastapi_poe as fp
from modal import App, Image, asgi_app

from wrapper_bot import WrapperBot
from bot_CafeMaid import CafeMaidBot
from bot_ChineseStatement import ChineseStatementBot
from bot_ChineseVocab import ChineseVocabBot
from bot_CmdLine import CmdLineBot
from bot_EnglishDiffBot import EnglishDiffBot


REQUIREMENTS = [
    "fastapi-poe==0.0.48", 
    "openai",
    "pandas",
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
    .copy_local_file("chinese_sentences.txt", "/root/chinese_sentences.txt")  # ChineseStatement
    .copy_local_file("chinese_words.csv", "/root/chinese_words.csv")
)
app = App("wrapper-bot-poe")


@app.function(image=image)
@asgi_app()
def fastapi_app():
    POE_ACCESS_KEY = os.environ["POE_ACCESS_KEY"]
    # see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
    # app = fp.make_app(bot, access_key=POE_ACCESS_KEY, bot_name=<YOUR_BOT_NAME>)
    app = fp.make_app(
        [
            WrapperBot(path="/WrapperBotDemo", access_key=POE_ACCESS_KEY),
            CafeMaidBot(path="/CafeMaid", access_key=POE_ACCESS_KEY),
            ChineseStatementBot(path="/ChineseStatement", access_key=POE_ACCESS_KEY),
            ChineseVocabBot(path="/ChineseVocab", access_key=POE_ACCESS_KEY),
            CmdLineBot(path="/CmdLine", access_key=POE_ACCESS_KEY),
            EnglishDiffBot(path="/EnglishDiffBot", access_key=POE_ACCESS_KEY),
        ],
    )
    return app
