"""

BOT_NAME="ChineseStatement"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

There are three states in the conversation
- Before getting the problem
- After getting the problem, before making a submission
- After making a submission
"""

from __future__ import annotations

import random
import re
from typing import AsyncIterable

import fastapi_poe as fp
from fastapi_poe.types import PartialResponse
from modal import Dict, Image, Stub, asgi_app

stub = Stub("poe-bot-ChineseStatement")
stub.my_dict = Dict.new()

with open("chinese_sentences.txt") as f:
    srr = f.readlines()

pattern = r"A\.\d\s"  # e.g. "A.1 "

level_to_statements_and_context = []

context = {}

for line in srr:
    line = line.strip()
    if re.match(pattern, line):
        level_to_statements_and_context.append([])
        continue
    if line == "":
        continue
    if "A." in line:
        depth = line.count(".")
        context[f"{depth}"] = line
        context.pop("【", None)
        context.pop("（", None)
        for nex_depth in range(depth + 1, 10):
            context.pop(f"{nex_depth}", None)
        continue
    if "【" in line:
        context["【"] = line
        context.pop("（", None)
        continue
    if "（" in line:
        context["（"] = line
        continue

    # statement matching
    if "。" not in line and "？" not in line:
        continue
    if "甲" in line or "乙" in line:
        continue
    if "/" in line:
        continue
    if len(line) > 50:
        continue

    level_to_statements_and_context[-1].append((line.strip(), list(context.values())))


TEMPLATE_STARTING_REPLY = """
The statement sampled from HSK level {level} is

# {statement}

Please translate the sentence.
""".strip()

SYSTEM_TABULATION_PROMPT = """
You will test the user on the translation of a Chinese sentence.

The statement is {statement}

You will whether the user's translation captures the full meaning of the sentence.

If the user has  user's translation captures the full meaning of the sentence, end you reply with
- Your translation has captured the full meaning of the sentence.
""".strip()

FREEFORM_SYSTEM_PROMPT = """
You are a patient Chinese language teacher.

You will guide the conversation in ways that maximizes the learning of the Chinese language.

The context of the problem is {context}
"""

PASS_STATEMENT = "I will pass this sentence."

NEXT_STATEMENT = "I want another sentence."


def get_user_level_key(user_id):
    return f"ChineseVocab-level-{user_id}"


def get_conversation_info_key(conversation_id):
    return f"ChineseVocab-statement-{conversation_id}"


def get_conversation_submitted_key(conversation_id):
    return f"ChineseVocab-submitted-{conversation_id}"


class GPT35TurboAllCapsBot(fp.PoeBot):
    async def get_response(
        self, request: fp.QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        user_level_key = get_user_level_key(request.user_id)
        conversation_info_key = get_conversation_info_key(request.conversation_id)
        conversation_submitted_key = get_conversation_submitted_key(
            request.conversation_id
        )
        last_user_reply = request.query[-1].content
        print(last_user_reply)

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
            statement, context = random.choice(
                level_to_statements_and_context[level - 1]  # leveling is one indexed
            )
            statement_info = {"statement": statement, "context": context}
            stub.my_dict[conversation_info_key] = statement_info
            yield self.text_event(
                TEMPLATE_STARTING_REPLY.format(
                    statement=statement_info["statement"], level=level
                )
            )
            yield PartialResponse(text=PASS_STATEMENT, is_suggested_reply=True)
            return

        # retrieve the previously cached word
        statement_info = stub.my_dict[conversation_info_key]
        statement = statement_info["statement"]  # so that this can be used in f-string

        # if the submission is already made, continue as per normal
        if conversation_submitted_key in stub.my_dict:
            request.query = [
                {
                    "role": "system",
                    "content": FREEFORM_SYSTEM_PROMPT.format(
                        context=str(statement_info["context"])
                    ),
                }
            ] + request.query
            bot_reply = ""
            async for msg in fp.stream_request(request, "ChatGPT", request.access_key):
                bot_reply += msg.text
                yield msg.model_copy()
            print(bot_reply)
            return

        # otherwise, disable suggested replies
        yield fp.MetaResponse(
            text="",
            content_type="text/markdown",
            linkify=True,
            refetch_settings=False,
            suggested_replies=False,
        )

        request.query = [
            {
                "role": "system",
                "content": SYSTEM_TABULATION_PROMPT.format(statement=statement),
            }
        ] + request.query
        request.temperature = 0
        request.logit_bias = {"2746": -5, "36821": -10}  # "If"  # " |\n\n"

        bot_reply = ""
        async for msg in fp.stream_request(request, "ChatGPT", request.access_key):
            bot_reply += msg.text
            yield msg.model_copy()

        # make a judgement on correctness
        stub.my_dict[conversation_submitted_key] = True
        if "has captured the full meaning" in bot_reply:
            stub.my_dict[user_level_key] = level + 1
        else:
            stub.my_dict[user_level_key] = level - 1

        # deliver suggsted replies
        yield PartialResponse(
            text="What are other sentences with a similar structure?",
            is_suggested_reply=True,
        )
        yield PartialResponse(text=NEXT_STATEMENT, is_suggested_reply=True)

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies={"ChatGPT": 1, "GPT-3.5-Turbo": 1},
            introduction_message="Say 'start' to get the sentence to translate.",
        )


REQUIREMENTS = ["fastapi-poe==0.0.24", "pandas"]
image = (
    Image.debian_slim()
    .pip_install(*REQUIREMENTS)
    .copy_local_file("chinese_sentences.txt", "/root/chinese_sentences.txt")
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
