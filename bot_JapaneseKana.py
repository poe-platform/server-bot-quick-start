"""

BOT_NAME="JapaneseKana"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

question_tuple modes
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


df = pd.read_csv("japanese_kana.csv")
# using https://github.com/krmanik/HSK-3.0-words-list/tree/main/HSK%20List
# see also https://www.mdbg.net/chinese/dictionary?page=cedict

records = df.to_dict(orient="records")
records = [{k: v for k, v in record.items() if pd.notna(v)} for record in records]

QUESTION_TUPLE_TO_CORRECT_ANSWERS = defaultdict(list)
QUESTION_TUPLE_TO_WRONG_ANSWERS = defaultdict(list)
QUESTION_TUPLE_TO_QUESTION_TUPLE = defaultdict(set)

for row in records:
    for k, v in row.items():
        if "answer" in k:
            QUESTION_TUPLE_TO_CORRECT_ANSWERS[
                row["question"], row["type"], row["class"]
            ].append(v)
        if "wrong" in k:
            QUESTION_TUPLE_TO_WRONG_ANSWERS[
                row["question"], row["type"], row["class"]
            ].append(v)
    del row

for row1 in records:
    for row2 in records:
        for k1, v1 in row1.items():
            if "answer" in k1 or "wrong" in k1:
                if v1 == row2["question"]:
                    QUESTION_TUPLE_TO_QUESTION_TUPLE[
                        row1["question"], row1["type"], row1["class"]
                    ].add((row2["question"], row2["type"], row2["class"]))
                    QUESTION_TUPLE_TO_QUESTION_TUPLE[
                        row2["question"], row2["type"], row2["class"]
                    ].add((row1["question"], row1["type"], row1["class"]))
        del row2
    del row1

# print("QUESTION_TUPLE_TO_CORRECT_ANSWERS", QUESTION_TUPLE_TO_CORRECT_ANSWERS)
# print("QUESTION_TUPLE_TO_WRONG_ANSWERS", QUESTION_TUPLE_TO_WRONG_ANSWERS)
# print("QUESTION_TUPLE_TO_QUESTION_TUPLE", QUESTION_TUPLE_TO_QUESTION_TUPLE['ju', 'romaji_to_hiragana_base'])

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

STATEMENT_WRONG = "\\[ \\textcolor{{red}}{{\\text{{\\textbf{{The expected answer is}}}}}} \\]\n\n# {answers}"


DISABLE_OPTIONS_COMMAND = "I do not need options."

ENABLE_OPTIONS_COMMAND = "I want to see options."

VERSION = "v17"


def get_user_options_key(user_id):
    assert user_id.startswith("u")
    return f"JapaneseKana-options-{user_id}"


def get_user_attempts_key(user_id):
    assert user_id.startswith("u")
    return f"JapaneseKana-attempts-{VERSION}-{user_id}"


def get_user_failures_key(user_id):
    assert user_id.startswith("u")
    return f"JapaneseKana-failures-{VERSION}-{user_id}"


def get_conversation_question_key(conversation_id):
    assert conversation_id.startswith("c")
    return f"JapaneseKana-question_tuple-{VERSION}-{conversation_id}"


def get_conversation_answers_key(conversation_id):
    assert conversation_id.startswith("c")
    return f"JapaneseKana-answers-{VERSION}-{conversation_id}"


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
            k: 1.5 / len(QUESTION_TUPLE_TO_CORRECT_ANSWERS)
            for k in QUESTION_TUPLE_TO_CORRECT_ANSWERS.keys()
        }
        if user_failures_key in my_dict:
            user_failures = my_dict[user_failures_key]

        user_attempts = {
            k: 3 / len(QUESTION_TUPLE_TO_CORRECT_ANSWERS)
            for k in QUESTION_TUPLE_TO_CORRECT_ANSWERS.keys()
        }
        # print("user_attempts", user_attempts)
        if user_attempts_key in my_dict:
            user_attempts = my_dict[user_attempts_key]

        old_question = None
        if conversation_answers_key in my_dict and conversation_question_key in my_dict:
            question_tuple = my_dict[conversation_question_key]
            answers = my_dict[conversation_answers_key]
            old_question = question_tuple
            # print(user_attempts)
            for answer in answers:
                if compare_answer(last_message, answer):
                    # actions if correct
                    print("correct")
                    yield self.text_event(STATEMENT_CORRECT)
                    user_attempts[question_tuple] += 1

                    for question_tuple_related in QUESTION_TUPLE_TO_QUESTION_TUPLE[
                        question_tuple
                    ]:
                        print(question_tuple_related)
                        user_attempts[question_tuple_related] += 0.1

                    for (
                        question_tuple_related
                    ) in QUESTION_TUPLE_TO_CORRECT_ANSWERS.keys():
                        if (
                            question_tuple_related[1] == question_tuple[1]
                        ):  # same question type
                            user_attempts[question_tuple_related] += 0.01

                    break
            else:
                # actions if wrong
                print("wrong")
                print(STATEMENT_WRONG)
                yield self.text_event(
                    STATEMENT_WRONG.format(answers=" / ".join(answers))
                )
                user_failures[question_tuple] += 1
                user_attempts[question_tuple] += 1

                for question_tuple_related in QUESTION_TUPLE_TO_QUESTION_TUPLE[
                    question_tuple
                ]:
                    user_failures[question_tuple_related] += 0.1
                    user_attempts[question_tuple_related] += 0.1

                for question_tuple_related in QUESTION_TUPLE_TO_CORRECT_ANSWERS.keys():
                    if (
                        question_tuple_related[-1] == question_tuple[-1]
                    ):  # same question class
                        user_failures[question_tuple_related] += 0.01
                        user_attempts[question_tuple_related] += 0.01

            my_dict[user_failures_key] = user_failures
            my_dict[user_attempts_key] = user_attempts
            yield self.text_event("\n\n---\n\n---\n\n---\n\n")

        # selection with upper confidence bound
        maxscore = 0
        maxquestion = 0

        t = sum(user_attempts.values()) - 1
        for question_tuple in QUESTION_TUPLE_TO_CORRECT_ANSWERS.keys():
            # TODO: apply filtering logic here
            if old_question == question_tuple:
                continue
            mean = user_failures[question_tuple] / user_attempts[question_tuple]
            c = 0.01
            # mean + c * sqrt(ln(t) / attempts)
            score = (
                mean
                + c * math.sqrt(math.log(t) / user_attempts[question_tuple])
                + random.randint(0, 1) / 10
            )
            if score > maxscore:
                maxscore = score
                maxquestion = question_tuple

        question_tuple = maxquestion

        yield self.text_event(
            f"{user_attempts[question_tuple] - user_failures[question_tuple]:.2f} / {user_attempts[question_tuple]:.2f} | {maxscore:.4f}\n\n"
        )

        my_dict[conversation_answers_key] = QUESTION_TUPLE_TO_CORRECT_ANSWERS[
            question_tuple
        ]
        my_dict[conversation_question_key] = question_tuple

        question_content, question_type, question_class = question_tuple
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

        options = [x for x in QUESTION_TUPLE_TO_WRONG_ANSWERS[question_tuple]]

        if my_dict[user_options_key]:
            options = set(options)
            options = list(options)[:3] + [
                random.choice(QUESTION_TUPLE_TO_CORRECT_ANSWERS[question_tuple])
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
            allow_attachments=False,
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
