# TODO - write script to update settings

"""
modal deploy bot_all.py

modal app stop wrapper-bot-poe && modal deploy bot_all.py
"""

from __future__ import annotations
import os

import fastapi_poe as fp
from modal import App, Image, asgi_app

from bot_CafeMaid import CafeMaidBot
from bot_ChineseStatement import ChineseStatementBot
from bot_ChineseVocab import ChineseVocabBot
from bot_EnglishDiffBot import EnglishDiffBot
from bot_ImageRouter import ImageRouterBot
from bot_JapaneseKana import JapaneseKanaBot
from bot_KnowledgeTest import KnowledgeTestBot
from bot_ModelRouter import ModelRouterBot
from bot_PromotedAnswer import PromotedAnswerBot
from bot_RunPythonCode import RunPythonCodeBot
from bot_PythonAgent import PythonAgentBot, PythonAgentExBot, LeetCodeAgentBot
from bot_H1B import H1BBot
from bot_ToolReasoner import ToolReasonerBot
from bot_ResumeReview import ResumeReviewBot
from bot_TesseractOCR import TesseractOCRBot
from bot_tiktoken import TikTokenBot
from bot_TrinoAgent import TrinoAgentBot, TrinoAgentExBot
from bot_RunTrinoQuery import RunTrinoQueryBot
from bot_FlowchartPlotter import FlowChartPlotterBot


REQUIREMENTS = [
    "fastapi-poe==0.0.48", 
    "openai==1.54.4",  # WrapperBotDemo, ResumeReview
    "pandas",  # which version?
    "requests==2.31.0",  # PromotedAnswerBot, ResumeReview
    "beautifulsoup4==4.10.0",  # PromotedAnswerBot
    "pdftotext==2.2.2",  # ResumeReview
    "Pillow==9.5.0",  # ResumeReview
    "pytesseract==0.3.10",  # ResumeReview
    "python-docx",  # ResumeReview
    "tiktoken",  # tiktoken
    "trino",  # RunTrinoQuery, TrinoAgent
]
image = (
    Image.debian_slim()
    .apt_install(
        "ca-certificates",
        "fonts-liberation",
        "libasound2",
        "libatk-bridge2.0-0",
        "libatk1.0-0",
        "libc6",
        "libcairo2",
        "libcups2",
        "libdbus-1-3",
        "libexpat1",
        "libfontconfig1",
        "libgbm1",
        "libgcc1",
        "libglib2.0-0",
        "libgtk-3-0",
        "libnspr4",
        "libnss3",
        "libpango-1.0-0",
        "libpangocairo-1.0-0",
        "libstdc++6",
        "libx11-6",
        "libx11-xcb1",
        "libxcb1",
        "libxcomposite1",
        "libxcursor1",
        "libxdamage1",
        "libxext6",
        "libxfixes3",
        "libxi6",
        "libxrandr2",
        "libxrender1",
        "libxss1",
        "libxtst6",
        "lsb-release",
        "wget",
        "xdg-utils",
        "curl",
    )  # mermaid requirements
    .run_commands("curl -sL https://deb.nodesource.com/setup_18.x | bash -")
    .apt_install("nodejs")
    .run_commands("npm install -g @mermaid-js/mermaid-cli")
    .apt_install(
        "libpoppler-cpp-dev",
        "tesseract-ocr-eng",
    )  # document processing
    .pip_install(*REQUIREMENTS)
    .env(
        {
            "POE_ACCESS_KEY": os.environ["POE_ACCESS_KEY"],
            "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
            "TRINO_HOST_URL": os.environ["TRINO_HOST_URL"],  # TrinoAgent, RunTrinoQuery
            "TRINO_USERNAME": os.environ["TRINO_USERNAME"],  # TrinoAgent, RunTrinoQuery
            "TRINO_PASSWORD": os.environ["TRINO_PASSWORD"],  # TrinoAgent, RunTrinoQuery
        }
    )
    .copy_local_file("chinese_sentences.txt", "/root/chinese_sentences.txt")  # ChineseStatement
    .copy_local_file("chinese_words.csv", "/root/chinese_words.csv")  # ChineseVocab
    .copy_local_file("japanese_kana.csv", "/root/japanese_kana.csv")  # JapaneseKana
    .copy_local_file("mmlu.csv", "/root/mmlu.csv")  # KnowledgeTest
    .copy_local_file("h1b.csv", "/root/h1b.csv")  # H-1B
)
app = App("wrapper-bot-poe")


@app.function(image=image, container_idle_timeout=1200)
@asgi_app()
def fastapi_app():
    POE_ACCESS_KEY = os.environ["POE_ACCESS_KEY"]
    # see https://creator.poe.com/docs/quick-start#configuring-the-access-credentials
    # app = fp.make_app(bot, access_key=POE_ACCESS_KEY, bot_name=<YOUR_BOT_NAME>)
    app = fp.make_app(
        [
            CafeMaidBot(path="/CafeMaid", access_key=POE_ACCESS_KEY),
            ChineseStatementBot(path="/ChineseStatement", access_key=POE_ACCESS_KEY),
            ChineseVocabBot(path="/ChineseVocab", access_key=POE_ACCESS_KEY),
            EnglishDiffBot(path="/EnglishDiffBot", access_key=POE_ACCESS_KEY),
            ImageRouterBot(path="/ImageRouter", access_key=POE_ACCESS_KEY),
            JapaneseKanaBot(path="/JapaneseKana", access_key=POE_ACCESS_KEY),
            KnowledgeTestBot(path="/KnowledgeTest", access_key=POE_ACCESS_KEY),
            ModelRouterBot(path="/ModelRouter", access_key=POE_ACCESS_KEY),
            PromotedAnswerBot(path="/PromotedAnswer", access_key=POE_ACCESS_KEY),
            RunPythonCodeBot(path="/RunPythonCode", access_key=POE_ACCESS_KEY),
            PythonAgentBot(path="/PythonAgent", access_key=POE_ACCESS_KEY),
            PythonAgentExBot(path="/PythonAgentEx", access_key=POE_ACCESS_KEY),
            H1BBot(path="/H-1B", access_key=POE_ACCESS_KEY),
            ToolReasonerBot(path="/ToolReasoner", access_key=POE_ACCESS_KEY),
            ResumeReviewBot(path="/ResumeReview", access_key=POE_ACCESS_KEY),
            TesseractOCRBot(path="/TesseractOCR", access_key=POE_ACCESS_KEY),
            TikTokenBot(path="/tiktoken", access_key=POE_ACCESS_KEY),
            TrinoAgentBot(path="/TrinoAgent", access_key=POE_ACCESS_KEY),
            TrinoAgentExBot(path="/TrinoAgentEx", access_key=POE_ACCESS_KEY),
            RunTrinoQueryBot(path="/RunTrinoQuery", access_key=POE_ACCESS_KEY),
            LeetCodeAgentBot(path="/LeetCodeAgent", access_key=POE_ACCESS_KEY),
            FlowChartPlotterBot(path="/FlowChartPlotter", access_key=POE_ACCESS_KEY),
        ],
    )
    return app
