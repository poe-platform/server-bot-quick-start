"""

BOT_NAME="JapaneseKana"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Question modes
- kana -> romanji
- romanji -> kana (note that this is not one to one)
- (Future) multiple kana -> romanji
- (Future) romanji -> multiple kana (sampling becomes more complicated)

Correctness check
- Simply strip all non alphabet or kana and compare exact string

Users can opt to select whether to see options
- This option is open at the start of the conversation, or when the user has recently changed the option
- "I want to see options", "I don't want to see options"

Four options would be shown (if the user wants to see options)
- One that is correct
- Three randomly selected from the pool (avoiding collisions)
    - (future) one of which that is frequently confused with

I plan to use multi-armed bandit to select the hiragana
- To choose questions that they are likely to get wrong
- But for beginners we want them to get the easy hiragana correct rather than letting them suffer at hard characters

Todo
- refactor csv to type, question, answer, level, alt_*

There are no LLM calls for this bot.
"""

from __future__ import annotations

import random
import re
from typing import AsyncIterable

import fastapi_poe as fp
import pandas as pd
from modal import App, Dict, Image, asgi_app

app = App("poe-bot-JapaneseKana")
my_dict = Dict.from_name("dict-JapaneseKana", create_if_missing=True)

df = pd.read_csv("japanese_hiragana.csv")
# using https://github.com/krmanik/HSK-3.0-words-list/tree/main/HSK%20List
# see also https://www.mdbg.net/chinese/dictionary?page=cedict

HIRAGANA_TO_ROMAJI_MAP = {}
for _, row in df.iterrows():
    HIRAGANA_TO_ROMAJI_MAP[row.hiragana] = row.romaji

HIRAGANA_TO_ROMAJI_STARTING_QUESTION = """
Please write the following in romaji

# {hiragana}
""".strip()

DISABLE_OPTIONS_COMMAND = "I do not need options."

ENABLE_OPTIONS_COMMAND = "I want to see options."


def get_user_options_key(user_id):
    assert user_id.startswith("u")
    return f"JapaneseKana-options-{user_id}"


def get_conversation_menu_key(conversation_id):
    assert conversation_id.startswith("c")
    return f"JapaneseKana-level-{conversation_id}"


def get_conversation_question_key(conversation_id):
    assert conversation_id.startswith("c")
    return f"JapaneseKana-question-{conversation_id}"


# Pattern to keep lowercase, uppercase alphabets and Hiragana characters
pattern = r"[^a-zA-Z\u3040-\u309F]+"


def compare_answer(submission, reference):
    # Replace all non-matching characters with an empty string
    filtered_text = re.sub(pattern, "", submission)
    return filtered_text == reference


class GPT35TurboAllCapsBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        user_options_key = get_user_options_key(request.user_id)
        conversation_question_key = get_conversation_question_key(
            request.conversation_id
        )

        last_message = request.query[-1].content
        print(f"{last_message=}")

        if last_message == DISABLE_OPTIONS_COMMAND:
            my_dict[user_options_key] = False
            del my_dict[conversation_question_key]
        elif last_message == ENABLE_OPTIONS_COMMAND:
            my_dict[user_options_key] = True
            del my_dict[conversation_question_key]

        # disable suggested replies by default
        yield fp.MetaResponse(
            text="",
            content_type="text/markdown",
            linkify=True,
            refetch_settings=False,
            suggested_replies=False,
        )

        if conversation_question_key in my_dict:
            hiragana = my_dict[conversation_question_key]
            romaji = HIRAGANA_TO_ROMAJI_MAP[hiragana]
            if compare_answer(last_message, romaji):
                print("correct")
                yield self.text_event(f"You are correct.")
            else:
                print("wrong")
                yield self.text_event(f"The expected answer is `{romaji}`")
            yield self.text_event("\n\n---\n\n")

        hiragana = random.choice(list(HIRAGANA_TO_ROMAJI_MAP.keys()))
        romaji = HIRAGANA_TO_ROMAJI_MAP[hiragana]

        question_text = HIRAGANA_TO_ROMAJI_STARTING_QUESTION.format(hiragana=hiragana)
        yield self.text_event(question_text)

        my_dict[conversation_question_key] = hiragana

        if user_options_key not in my_dict:
            my_dict[user_options_key] = True

        if my_dict[user_options_key]:
            options = random.sample(list(HIRAGANA_TO_ROMAJI_MAP.values()), 7)
            options = set(options) - {romaji}
            options = list(options)[:3] + [romaji]
            random.shuffle(options)
            for option in options:
                yield self.suggested_reply_event(text=option)

        if len(request.query) == 2:
            if my_dict[user_options_key]:
                yield self.suggested_reply_event(text=DISABLE_OPTIONS_COMMAND)
            else:
                yield self.suggested_reply_event(text=ENABLE_OPTIONS_COMMAND)

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies={},
            introduction_message="Say 'start' to get the sample.",
        )


REQUIREMENTS = ["fastapi-poe==0.0.37", "pandas"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .copy_local_file("japanese_hiragana.csv", "/root/japanese_hiragana.csv")
)


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = GPT35TurboAllCapsBot()
    # Optionally, provide your Poe access key here:
    # 1. You can go to https://poe.com/create_bot?server=1 to generate an access key.
    # 2. We strongly recommend using a key for a production bot to prevent abuse,
    # but the starter examples disable the key check for convenience.
    # 3. You can also store your access key on modal.com and retrieve it in this function
    # by following the instructions at: https://modal.com/docs/guide/secrets
    # POE_ACCESS_KEY = ""
    # app = make_app(bot, access_key=POE_ACCESS_KEY)
    app = fp.make_app(bot, allow_without_key=True)
    return app
