"""

BOT_NAME="ChineseVocab"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

There are three states in the conversation
- Before getting the problem
- After getting the problem, before making a submission
- After making a submission
"""

from __future__ import annotations

import re
from typing import AsyncIterable

import fastapi_poe as fp
import pandas as pd
from fastapi_poe.types import PartialResponse, ProtocolMessage
from modal import Dict, Image, Stub, asgi_app

stub = Stub("poe-bot-ChineseVocab")
stub.my_dict = Dict.new()

df = pd.read_csv("chinese_words.csv")
# using https://github.com/krmanik/HSK-3.0-words-list/tree/main/HSK%20List
# see also https://www.mdbg.net/chinese/dictionary?page=cedict

TEMPLATE_STARTING_REPLY = """
The word sampled from HSK level {level} is

# {word}

Please provide the **pinyin** and a **meaning** of the word.
""".strip()

SYSTEM_TABULATION_PROMPT = """
You will test the user on the definition of a Chinese word.

The user will need to provide the pinyin pronounication and meaning of the word.
The pinyin provided needs to have the tones annotated.

The word is {word}
The reference pinyin is {pinyin}
The reference meaning is {meaning}

The user is expected to reply the pinyin and meaning.

When you receive the pinyin and meaning, reply with the following table. DO NOT ADD ANYTHING ELSE.

For example, if the user replies "mei2 shou1 confiscate", your reply will be

|             | Pinyin      | Meaning                 |
| ----------- | ----------- | ----------------------- |
| Your answer | mei2 shou1  | confiscate              |
| Reference   | mo4 shou1   | to confiscate, to seize |

REMINDER
- ALWAYS REPLY WITH THE TABLE.
- DO NOT ADD ANYTHING ELSE AFTER THE TABLE.
""".strip()

JUDGE_SYSTEM_PROMPT = """
You will judge the whether the user (in the row "your answer") has provided the correct pinyin, tone and meaning for the word {word}.

{reply}

You will start your reply with exactly one of, only based on the alphabets provided, ignoring the numerical tones

- The pinyin is correct.
- The pinyin is incorrect.
- The pinyin is missing.

You will exactly reply with one of, based on the numerical tone provided

- The numerical tone is correct.
- The numerical tone is incorrect
- The numerical tone is missing.

You will exactly reply with one of

- The meaning is correct.
- The meaning is missing.
- The meaning is incorrect.

REMINDER
- Follow the reply template.
- Do not add anything else in your reply.
- We consider the meaning correct if it matches any of the reference meanings.
- The reference meaning is not exhaustive. Accept the user's answer if it is correct, even it is not in the reference meaning
"""

FREEFORM_SYSTEM_PROMPT = """
You are a patient Chinese language teacher.

You will guide the conversation in ways that maximizes the learning of the Chinese language.

You will always use {format} characters.

The examples you provide will be as diverse as possible.

REMINDER: use {format} characters. {format_repeat}
"""

SUGGESTED_REPLIES_SYSTEM_PROMPT = """
You will suggest replies based on the conversation given by the user.
"""

SUGGESTED_REPLIES_USER_PROMPT = """
Read the conversation above.

Suggest three ways the user would continue the conversation.

Each suggestion should be concise.

The suggested replies could follow either of the following styles
- How do I use {word} in a sentence?
- What are some words related to {word}?
- Could you explain the difference between {word} and (word that looks similar)?
- What do the individual characters of {word} mean?
- What is the origin of the word {word}?

Begin each suggestion with <a> and end each suggestion with </a>.
Do not use inverted commas. Do not prefix each suggestion.
""".strip()

PASS_STATEMENT = "I will pass this word."

NEXT_STATEMENT = "I want another word."

TRADITIONAL_STATEMENT = "I prefer traditional characters."

SIMPLIFIED_STATEMENT = "I prefer simplified characters."

SUGGESTED_REPLIES_REGEX = re.compile(r"<a>(.+?)</a>", re.DOTALL)


def extract_suggested_replies(raw_output: str) -> list[str]:
    suggested_replies = [
        suggestion.strip() for suggestion in SUGGESTED_REPLIES_REGEX.findall(raw_output)
    ]
    return suggested_replies


def stringify_conversation(messages: list[ProtocolMessage]) -> str:
    stringified_messages = ""

    for message in messages:
        # NB: system prompt is intentionally excluded
        if message.role == "bot":
            stringified_messages += f"User: {message.content}\n\n"
        else:
            stringified_messages += f"Character: {message.content}\n\n"
    return stringified_messages


def get_user_format_key(user_id):
    assert user_id.startswith("u")
    # simplified or traditional
    return f"ChineseVocab-format-{user_id}"


def get_user_level_key(user_id):
    assert user_id.startswith("u")
    return f"ChineseVocab-level-{user_id}"


def get_conversation_info_key(conversation_id):
    assert conversation_id.startswith("c")
    return f"ChineseVocab-word-{conversation_id}"


def get_conversation_submitted_key(conversation_id):
    assert conversation_id.startswith("c")
    return f"ChineseVocab-submitted-{conversation_id}"


class GPT35TurboAllCapsBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        user_level_key = get_user_level_key(request.user_id)
        user_format_key = get_user_format_key(request.user_id)
        conversation_info_key = get_conversation_info_key(request.conversation_id)
        conversation_submitted_key = get_conversation_submitted_key(
            request.conversation_id
        )
        last_user_reply = request.query[-1].content
        print(last_user_reply)

        if last_user_reply in TRADITIONAL_STATEMENT:
            stub.my_dict[user_format_key] = "traditional"

        if last_user_reply in SIMPLIFIED_STATEMENT:
            stub.my_dict[user_format_key] = "simplified"

        if user_format_key in stub.my_dict:
            format = stub.my_dict[user_format_key]
        else:
            stub.my_dict[user_format_key] = "simplified"
            format = stub.my_dict[user_format_key]

        print(format)

        # reset if the user passes or asks for the next statement
        if last_user_reply in (NEXT_STATEMENT, PASS_STATEMENT):
            if conversation_info_key in stub.my_dict:
                stub.my_dict.pop(conversation_info_key)
            if conversation_submitted_key in stub.my_dict:
                stub.my_dict.pop(conversation_submitted_key)

        # retrieve the level of the user
        # TODO(when conversation starter is ready): jump to a specific level
        if last_user_reply in "1234567":
            level = int(last_user_reply)
            stub.my_dict[user_level_key] = level
        elif user_level_key in stub.my_dict:
            level = stub.my_dict[user_level_key]
            level = max(1, level)
            level = min(7, level)
        else:
            level = 1
            stub.my_dict[user_level_key] = level

        # for new conversations, sample a problem
        if conversation_info_key not in stub.my_dict:
            word_info = (
                df[(df["level"] == level) & (df["exclude"] == False)]
                .sample(n=1)
                .to_dict(orient="records")[0]
            )
            stub.my_dict[conversation_info_key] = word_info
            yield self.text_event(
                TEMPLATE_STARTING_REPLY.format(
                    word=word_info[format], level=word_info["level"]
                )
            )

            if word_info["simplified"] != word_info["traditional"]:
                if format == "simplified":
                    yield PartialResponse(
                        text=TRADITIONAL_STATEMENT, is_suggested_reply=True
                    )
                else:
                    yield PartialResponse(
                        text=SIMPLIFIED_STATEMENT, is_suggested_reply=True
                    )

            yield PartialResponse(text=PASS_STATEMENT, is_suggested_reply=True)
            return

        # retrieve the previously cached word
        word_info = stub.my_dict[conversation_info_key]
        word = word_info[format]  # so that this can be used in f-string

        if last_user_reply in (TRADITIONAL_STATEMENT, SIMPLIFIED_STATEMENT):
            yield self.text_event(
                TEMPLATE_STARTING_REPLY.format(
                    word=word_info[format], level=word_info["level"]
                )
            )
            yield PartialResponse(text=PASS_STATEMENT, is_suggested_reply=True)
            return

        # if the submission is already made, continue as per normal
        if conversation_submitted_key in stub.my_dict:
            format_repeat = "请使用简体中文。" if format == "simplified" else "請使用繁體中文。"

            request.query = [
                ProtocolMessage(role="system", content=FREEFORM_SYSTEM_PROMPT.format(format=format, format_repeat=format_repeat))
            ] + [
                ProtocolMessage(role="system", content=format_repeat)
            ] + request.query
            bot_reply = ""
            async for msg in fp.stream_request(request, "ChatGPT", request.access_key):
                bot_reply += msg.text
                yield msg.model_copy()
            print(bot_reply)

            request.query = request.query + [
                ProtocolMessage(role="bot", content=bot_reply)
            ]
            current_conversation_string = stringify_conversation(request.query)

            request.query = [
                ProtocolMessage(role="system", content=SUGGESTED_REPLIES_SYSTEM_PROMPT),
                ProtocolMessage(role="user", content=current_conversation_string),
                ProtocolMessage(
                    role="user", content=SUGGESTED_REPLIES_USER_PROMPT.format(word=word)
                ),
            ]
            response_text = ""
            async for msg in fp.stream_request(request, "ChatGPT", request.access_key):
                response_text += msg.text
            print("suggested_reply", response_text)

            suggested_replies = extract_suggested_replies(response_text)

            for suggested_reply in suggested_replies[:3]:
                yield PartialResponse(text=suggested_reply, is_suggested_reply=True)
            yield PartialResponse(text=NEXT_STATEMENT, is_suggested_reply=True)
            return

        # otherwise, disable suggested replies
        yield fp.MetaResponse(
            text="",
            content_type="text/markdown",
            linkify=True,
            refetch_settings=False,
            suggested_replies=False,
        )

        # tabluate the user's submission
        request.query = [
            {
                "role": "system",
                "content": SYSTEM_TABULATION_PROMPT.format(
                    word=word_info["simplified"],
                    pinyin=word_info["numerical_pinyin"],
                    meaning=word_info["translation"],
                ),
            }
        ] + request.query
        request.temperature = 0
        request.logit_bias = {"2746": -5, "36821": -10}  # "If"  # " |\n\n"

        bot_reply = ""
        async for msg in fp.stream_request(request, "ChatGPT", request.access_key):
            bot_reply += msg.text
            yield msg.model_copy()

        yield self.text_event("\n\n")

        # make a judgement on correctness
        if "-----" in bot_reply:
            stub.my_dict[conversation_submitted_key] = True
            request.query = [
                {
                    "role": "user",
                    "content": JUDGE_SYSTEM_PROMPT.format(reply=bot_reply, word=word),
                }
            ]
            request.temperature = 0
            judge_reply = ""
            async for msg in fp.stream_request(
                request, "GPT-3.5-Turbo", request.access_key
            ):
                judge_reply += msg.text
                # yield self.text_event(msg.text)

            yield self.text_event("\n\n")
            yield self.text_event(
                "You can reset the context (brush icon on bottom left) if you want a new word.\nYou can also follow up with asking more about the word."
            )

            print(judge_reply, judge_reply.count(" correct"))
            if (
                "pinyin is correct" in judge_reply
                and "tone is correct" in judge_reply
                and "meaning is correct" in judge_reply
                and word_info["numerical_pinyin"] in last_user_reply
            ):
                stub.my_dict[user_level_key] = level + 1
            elif (
                judge_reply.count(" correct") == 0
            ):  # NB: note the space otherwise it matches incorrect
                stub.my_dict[user_level_key] = level - 1

            # deliver suggested replies
            yield PartialResponse(
                text=f"What are some ways to use {word} in a sentence?",
                is_suggested_reply=True,
            )
            yield PartialResponse(
                text=f"What are some words related to {word}?", is_suggested_reply=True
            )
            yield PartialResponse(text=NEXT_STATEMENT, is_suggested_reply=True)
        else:
            yield PartialResponse(text=NEXT_STATEMENT, is_suggested_reply=True)

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies={"ChatGPT": 1, "GPT-3.5-Turbo": 1},
            introduction_message="Say 'start' to get the Chinese word.",
        )


REQUIREMENTS = ["fastapi-poe==0.0.24", "pandas"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .copy_local_file("chinese_words.csv", "/root/chinese_words.csv")
)


@stub.function(image=image)
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
