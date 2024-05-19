"""

BOT_NAME="LeetCodeAgent"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
(copy some leetcode problem)

"""

import os

from fastapi_poe import make_app
from modal import asgi_app

import bot_PythonAgent
from bot_PythonAgent import PythonAgentBot, app, image_bot

bot_PythonAgent.PYTHON_AGENT_SYSTEM_PROMPT = """
You will write the solution to a Leetcode problem.

Implement your code as a method in the `class Solution`.

Write test cases in this format. Do not create new test cases, only use the given test cases.

s = Solution()
print(s.<function>(<inputs>))  # Expected: <expected output>
print(s.<function>(<inputs>))  # Expected: <expected output>
""".strip()

bot_PythonAgent.CODE_WITH_WRAPPERS = """\
from typing import *
from collections import *
import collections
import itertools
import numpy as np

import dill, os, pickle
if os.path.exists("{conversation_id}.dill"):
    try:
        with open("{conversation_id}.dill", 'rb') as f:
            dill.load_session(f)
    except:
        pass

{code}

with open('{conversation_id}.dill', 'wb') as f:
    dill.dump_session(f)
"""

bot_PythonAgent.SIMULATED_USER_REPLY_NO_OUTPUT_OR_ERROR = """\
Write the code to test the solution with the example test cases.
Do not create new test cases.

Write test cases in this format

s = Solution()
print(s.<function>(<inputs>))  # Expected: <expected output>
print(s.<function>(<inputs>))  # Expected: <expected output>

Do not repeat the solution.
"""

bot_PythonAgent.SIMULATED_USER_REPLY_OUTPUT_ONLY = """\
The code was executed and this is the output.
```output
{output}
```

Read the output and check whether is it wrong.

If there is an issue, you will first hand-calculate (without code) the expected intermediate values. Then, check those values by printing the intermediate values, making sure that the intermediate values are printed.

If the output looks ok, meticulously calculate the complexity of the solution to check whether it is within the time limit. (Note: "105" is likely 10**5). Fix the code if it is likely to exceed time limit.

Do not present the final code for reference.
"""

bot_PythonAgent.SIMULATED_USER_SUFFIX_PROMPT = ""

bot = PythonAgentBot()
bot.prompt_bot = "GPT-4o-128k"
bot.code_iteration_limit = 10
bot.system_prompt_role = "user"


@app.function(image=image_bot, container_idle_timeout=1200)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
