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

import math
import random
import re
from collections import defaultdict
from typing import AsyncIterable

import fastapi_poe as fp
import pandas as pd
from modal import App, Dict, Image, asgi_app

app = App("poe-bot-JapaneseKana")
my_dict = Dict.from_name("dict-JapaneseKana", create_if_missing=True)

df = pd.read_csv("japanese_kana.csv")
# using https://github.com/krmanik/HSK-3.0-words-list/tree/main/HSK%20List
# see also https://www.mdbg.net/chinese/dictionary?page=cedict


QUESTION_TO_CORRECT_ANSWERS = defaultdict(list)
QUESTION_TO_WRONG_ANSWERS = defaultdict(list)

for index, row in df.iterrows():
    row_dict = row.dropna().to_dict()
    for k, v in row_dict.items():
        if "answer" in k:
            QUESTION_TO_CORRECT_ANSWERS[row.question, row.type].append(v)
        if "wrong" in k:
            QUESTION_TO_WRONG_ANSWERS[row.question, row.type].append(v)

# print("QUESTION_TO_CORRECT_ANSWERS", QUESTION_TO_CORRECT_ANSWERS)
# print("QUESTION_TO_WRONG_ANSWERS", QUESTION_TO_WRONG_ANSWERS)

KANA_TO_ROMAJI_STARTING_QUESTION = """
What is this in romaji?

# {kana}
""".strip()


ROMAJI_TO_HIRAGANA_STARTING_QUESTION = """
What is this in hiragana?

# {romaji}
""".strip()


ROMAJI_TO_KATAKANA_STARTING_QUESTION = """
What is this in katakana?

# {romaji}
""".strip()


STATEMENT_CORRECT = (
    f"\\[ \\textcolor{{green}}{{\\text{{\\textbf{{You are correct}}}}}} \\]"
)

STATEMENT_WRONG = "\\[ \\textcolor{{red}}{{\\text{{\\textbf{{The expected answer is {answers}}}}}}} \\]"


DISABLE_OPTIONS_COMMAND = "I do not need options."

ENABLE_OPTIONS_COMMAND = "I want to see options."


def get_user_options_key(user_id):
    assert user_id.startswith("u")
    return f"JapaneseKana-options-{user_id}"


def get_user_attempts_key(user_id):
    assert user_id.startswith("u")
    return f"JapaneseKana-attempts-v9-{user_id}"


def get_user_failures_key(user_id):
    assert user_id.startswith("u")
    return f"JapaneseKana-failures-v9-{user_id}"


def get_conversation_menu_key(conversation_id):
    assert conversation_id.startswith("c")
    return f"JapaneseKana-level-{conversation_id}"


def get_conversation_question_key(conversation_id):
    assert conversation_id.startswith("c")
    return f"JapaneseKana-question-{conversation_id}"


def get_conversation_answers_key(conversation_id):
    assert conversation_id.startswith("c")
    return f"JapaneseKana-answers-{conversation_id}"


# Pattern to keep lowercase, uppercase alphabets and Hiragana characters
pattern = r"[^a-zA-Z\u3040-\u309F\u30A0-\u30FF]+"


def compare_answer(submission, reference):
    # Replace all non-matching characters with an empty string
    filtered_text = re.sub(pattern, "", submission)
    return filtered_text == reference


class GPT35TurboAllCapsBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        user_options_key = get_user_options_key(request.user_id)
        conversation_answers_key = get_conversation_answers_key(request.conversation_id)
        conversation_question_key = get_conversation_question_key(
            request.conversation_id
        )
        user_failures_key = get_user_failures_key(request.user_id)
        user_attempts_key = get_user_attempts_key(request.user_id)

        last_message = request.query[-1].content

        if last_message == DISABLE_OPTIONS_COMMAND:
            my_dict[user_options_key] = False
            del my_dict[conversation_answers_key]
        elif last_message == ENABLE_OPTIONS_COMMAND:
            my_dict[user_options_key] = True
            del my_dict[conversation_answers_key]

        # disable suggested replies by default
        yield fp.MetaResponse(
            text="",
            content_type="text/markdown",
            linkify=True,
            refetch_settings=False,
            suggested_replies=False,
        )

        user_failures = {
            k: 1.5 / len(QUESTION_TO_CORRECT_ANSWERS)
            for k in QUESTION_TO_CORRECT_ANSWERS.keys()
        }
        if user_failures_key in my_dict:
            user_failures = my_dict[user_failures_key]

        user_attempts = {
            k: 3 / len(QUESTION_TO_CORRECT_ANSWERS)
            for k in QUESTION_TO_CORRECT_ANSWERS.keys()
        }
        print("user_attempts", user_attempts)
        if user_attempts_key in my_dict:
            user_attempts = my_dict[user_attempts_key]

        old_question = None
        if conversation_answers_key in my_dict and conversation_question_key in my_dict:
            question = my_dict[conversation_question_key]
            answers = my_dict[conversation_answers_key]
            old_question = question
            print(user_attempts)
            for answer in answers:
                if compare_answer(last_message, answer):
                    # actions if correct
                    print("correct")
                    yield self.text_event(STATEMENT_CORRECT)
                    user_attempts[question] += 1
                    break
            else:
                # actions if wrong
                print("wrong")
                print(STATEMENT_WRONG)
                yield self.text_event(
                    STATEMENT_WRONG.format(answers=" / ".join(answers))
                )
                user_attempts[question] += 1
                user_failures[question] += 1

            my_dict[user_failures_key] = user_failures
            my_dict[user_attempts_key] = user_attempts
            yield self.text_event(
                f"\n\n{user_attempts[question] - user_failures[question]:.1f} / {user_attempts[question]:.1f}\n\n"
            )
            yield self.text_event("\n\n---\n\n")

        maxscore = 0
        maxquestion = 0

        t = sum(user_attempts.values()) - 1
        for question in QUESTION_TO_CORRECT_ANSWERS.keys():
            # TODO: apply filtering logic here
            if old_question == question:
                continue
            mean = user_failures[question] / user_attempts[question]
            # mean + sqrt(ln(t) / attempts)
            score = (
                mean
                + math.sqrt(math.log(t) / user_attempts[question])
                + random.random() * 0.01
            )
            if score > maxscore:
                maxscore = score
                maxquestion = question

        yield self.text_event(f"{maxscore:.4f}\n\n")

        question = maxquestion

        my_dict[conversation_answers_key] = QUESTION_TO_CORRECT_ANSWERS[question]
        my_dict[conversation_question_key] = question

        question_content, question_type = question
        if question_type == "hiragana_to_romaji_base":
            question_text = KANA_TO_ROMAJI_STARTING_QUESTION.format(
                kana=question_content
            )
            yield self.text_event(question_text)
        elif question_type == "katakana_to_romaji_base":
            question_text = KANA_TO_ROMAJI_STARTING_QUESTION.format(
                kana=question_content
            )
            yield self.text_event(question_text)
        elif question_type == "romaji_to_hiragana_base":
            question_text = ROMAJI_TO_HIRAGANA_STARTING_QUESTION.format(
                romaji=question_content
            )
            yield self.text_event(question_text)
        elif question_type == "romaji_to_katakana_base":
            question_text = ROMAJI_TO_KATAKANA_STARTING_QUESTION.format(
                romaji=question_content
            )
            yield self.text_event(question_text)

        if user_options_key not in my_dict:
            my_dict[user_options_key] = True

        options = [x for x in QUESTION_TO_WRONG_ANSWERS[question]]

        if my_dict[user_options_key]:
            options = set(options)
            options = list(options)[:3] + [
                random.choice(QUESTION_TO_CORRECT_ANSWERS[question])
            ]
            print("options", options)
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
    .copy_local_file("japanese_kana.csv", "/root/japanese_kana.csv")
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
