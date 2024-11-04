"""

BOT_NAME="PythonAgentEx"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
download and save wine dataset
list directory

"""

import re
import textwrap
import keyword
from bot_PythonAgent import PythonAgentBot


PYTHON_AGENT_SYSTEM_PROMPT = """
You will write Python code to solve the given problem.

Directly execute the calculations in the main scope, dot no wrap in a function.
""".strip()


def process_python_code(query):
    # Add import statements
    # Also print variables if they are not inside any indentation
    query = "import math\nimport numpy as np\nimport sympy as sp\n" + query
    current_rows = query.strip().split("\n")
    new_rows = []
    for row in current_rows:
        new_rows.append(row)
        if not row.startswith(" ") and "=" in row:
            variables_to_print = row.split("=")[0].strip()
            for variable_to_print in variables_to_print.split(","):
                variable_to_print = variable_to_print.strip()
                if variable_to_print.isidentifier() and not keyword.iskeyword(variable_to_print):
                    new_rows.append(f'\ntry:\n    print(f"{variable_to_print}={{str({variable_to_print})[:100]}}")\nexcept:\n    pass\n')
    return "\n".join(new_rows)


class ToolReasonerBot(PythonAgentBot):
    prompt_bot = "Claude-3.5-Sonnet"
    code_iteration_limit = 5
    system_prompt_role = "system"
    python_agent_system_prompt = PYTHON_AGENT_SYSTEM_PROMPT

    def extract_code(self, text):
        def extract_code_inner(text):
            pattern = r"\n```python([\s\S]*?)\n```"
            matches = re.findall(pattern, "\n" + text)
            if matches:
                return "\n\n".join(matches)

            pattern = r"```python([\s\S]*?)```"
            matches = re.findall(pattern, "\n" + text)
            return "\n\n".join(textwrap.dedent(match) for match in matches)

        code = extract_code_inner(text)
        if not code:
             return ""
        return process_python_code(code)
    