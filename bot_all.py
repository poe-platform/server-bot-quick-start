# TODO - write script to update settings

from __future__ import annotations
import os

import fastapi_poe as fp
from modal import App, Image, asgi_app

from wrapper_bot import WrapperBot
from bot_CafeMaid import CafeMaidBot
from bot_ChineseStatement import ChineseStatementBot
from bot_ChineseVocab import ChineseVocabBot
from bot_EnglishDiffBot import EnglishDiffBot
from bot_ImageRouter import ImageRouterBot
from bot_JapaneseKana import JapaneseKanaBot
from bot_KnowledgeTest import KnowledgeTestBot
from bot_ModelRouter import ModelRouterBot
from bot_PromotedAnswer import PromotedAnswerBot
from bot_PythonAgent import PythonAgentBot
from bot_PythonAgentEx import PythonAgentExBot
from bot_H1B import H1BBot

REQUIREMENTS = [
    "fastapi-poe==0.0.48", 
    "openai",  # WrapperBotDemo
    "pandas",  # which version?
    "requests==2.31.0",  # PromotedAnswerBot
    "beautifulsoup4==4.10.0",  # PromotedAnswerBot
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
    .copy_local_file("chinese_words.csv", "/root/chinese_words.csv")  # ChineseVocab
    .copy_local_file("japanese_kana.csv", "/root/japanese_kana.csv")  # JapaneseKana
    .copy_local_file("mmlu.csv", "/root/mmlu.csv")  # KnowledgeTest
    .copy_local_file("h1b.csv", "/root/h1b.csv")  # H-1B
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
            EnglishDiffBot(path="/EnglishDiffBot", access_key=POE_ACCESS_KEY),
            ImageRouterBot(path="/ImageRouter", access_key=POE_ACCESS_KEY),
            JapaneseKanaBot(path="/JapaneseKana", access_key=POE_ACCESS_KEY),
            KnowledgeTestBot(path="/KnowledgeTest", access_key=POE_ACCESS_KEY),
            ModelRouterBot(path="/ModelRouter", access_key=POE_ACCESS_KEY),
            PromotedAnswerBot(path="/PromotedAnswer", access_key=POE_ACCESS_KEY),
            PythonAgentBot(path="/PythonAgent", access_key=POE_ACCESS_KEY),
            PythonAgentExBot(path="/PythonAgentEx", access_key=POE_ACCESS_KEY),
            H1BBot(path="/H-1B", access_key=POE_ACCESS_KEY),
        ],
    )
    return app
