"""

BOT_NAME="PythonAgentEx"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
download and save wine dataset
list directory

"""

from bot_PythonAgent import PythonAgentBot


class PythonAgentExBot(PythonAgentBot):
    prompt_bot = "o1-mini"
    code_iteration_limit = 5
    system_prompt_role = "user"