"""

BOT_NAME="H-1B"; modal deploy --name $BOT_NAME bot_${BOT_NAME}.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

Test message:
How many h1b1 were issued?

"""

import os

import modal
from fastapi_poe import make_app
from modal import Stub, asgi_app

import bot_PythonAgent
from bot_PythonAgent import PythonAgentBot

# https://modalbetatesters.slack.com/archives/C031Z7H15DG/p1675177408741889?thread_ts=1675174647.477169&cid=C031Z7H15DG
modal.app._is_container_app = False

bot_PythonAgent.PYTHON_AGENT_SYSTEM_PROMPT = """
You have access to the H-1B dataset in df.csv.
You write the Python code to answer my queries, whenever possible.

When you return Python code
- Encapsulate all Python code within triple backticks (i.e ```python) with newlines.
- The Python code should either print something or plot something
- When filtering rows by <class 'str'> columns, always use .str.contains(<string>, case=False) instead of ==
- The Python code should start with `df = pd.read_csv('/df.csv')` (NOTE: this is in the root directory /)

df.csv contains information about Labor application information from H-1B, H-1B1, and E-3 Programs.

df.csv contains the following columns
- 'CASE_NUMBER'
- 'CASE_STATUS',
- 'RECEIVED_DATE'
- 'DECISION_DATE'
- 'ORIGINAL_CERT_DATE'
- 'VISA_CLASS'
- 'JOB_TITLE'
- 'SOC_TITLE'
- 'FULL_TIME_POSITION'
- 'BEGIN_DATE'
- 'END_DATE'
- 'EMPLOYER_NAME'
- 'AGENT_REPRESENTING_EMPLOYER'
- 'LAWFIRM_NAME_BUSINESS_NAME'
- 'SECONDARY_ENTITY'
- 'SECONDARY_ENTITY_BUSINESS_NAME'
- 'WORKSITE_STATE'
- 'WAGE_RATE_OF_PAY_FROM'
- 'WAGE_RATE_OF_PAY_TO'
- 'WAGE_UNIT_OF_PAY'
- 'YEAR'
- 'QUARTER'


The five most common values for each column is as listed.

I-200-20281-869622    5
I-200-20329-926703    5
I-200-20281-866764    5
I-200-20283-875087    5
I-200-20281-868228    5
Name: CASE_NUMBER, type: <class 'str'>

Certified                2366621
Certified - Withdrawn     118268
Withdrawn                  47581
Denied                     13921
Name: CASE_STATUS, type: <class 'str'>

2020-10-07 00:00:00    30757
2020-12-09 00:00:00    14006
2020-12-10 00:00:00     9146
2020-12-14 00:00:00     6610
2020-12-11 00:00:00     6436
Name: RECEIVED_DATE, type: <class 'str'>

2020-10-15 00:00:00    29251
2020-12-16 00:00:00    13401
2020-12-17 00:00:00     9003
2020-11-25 00:00:00     8926
2021-02-22 00:00:00     6950
Name: DECISION_DATE, type: <class 'str'>

2020-10-15 00:00:00    1257
2020-12-16 00:00:00     548
2021-06-25 00:00:00     534
2020-05-13 00:00:00     406
2021-04-22 00:00:00     381
Name: ORIGINAL_CERT_DATE, type: <class 'float'>

H-1B               2481378
E-3 Australian       51029
H-1B1 Chile           7802
H-1B1 Singapore       6182
Name: VISA_CLASS, type: <class 'str'>

SOFTWARE ENGINEER              137371
SOFTWARE DEVELOPER             101873
SENIOR SOFTWARE ENGINEER        37190
MANAGER JC50                    25504
SENIOR SYSTEMS ANALYST JC60     22488
Name: JOB_TITLE, type: <class 'str'>

Software Developers, Applications        624758
Software Developers                      209165
Computer Systems Analysts                160672
Software Developers, Systems Software    116219
Computer Systems Engineers/Architects     86964
Name: SOC_TITLE, type: <class 'str'>

Y    2506698
N      39693
Name: FULL_TIME_POSITION, type: <class 'str'>

2022-10-01 00:00:00    102403
2020-10-01 00:00:00     89445
2021-10-01 00:00:00     85991
2023-10-01 00:00:00     71318
2021-01-01 00:00:00     14035
Name: BEGIN_DATE, type: <class 'str'>

2025-09-30 00:00:00    100715
2024-09-30 00:00:00     87862
2023-09-30 00:00:00     86452
2026-09-30 00:00:00     69101
2024-06-30 00:00:00     13131
Name: END_DATE, type: <class 'str'>

COGNIZANT TECHNOLOGY SOLUTIONS US CORP    74619
AMAZON.COM SERVICES LLC                   54156
GOOGLE LLC                                48220
TATA CONSULTANCY SERVICES LIMITED         44031
ERNST & YOUNG U.S. LLP                    40673
Name: EMPLOYER_NAME, type: <class 'str'>

Yes    1438149
No      530908
Y       405668
N       171666
Name: AGENT_REPRESENTING_EMPLOYER, type: <class 'str'>

FRAGOMEN, DEL REY, BERNSEN & LOEWY, LLP           261280
BERRY APPLEMAN & LEIDEN LLP                       141684
FRAGOMEN, DEL REY, BERNSEN & LOEWY LLP             50628
OGLETREE, DEAKINS, NASH, SMOAK & STEWART, P.C.     45981
SEYFARTH SHAW LLP                                  38399
Name: LAWFIRM_NAME_BUSINESS_NAME, type: <class 'str'>

No     1515532
Yes     453525
N       376986
Y       198387
Name: SECONDARY_ENTITY, type: <class 'str'>

WELLS FARGO             6375
FORD MOTOR COMPANY      5562
VERIZON                 4821
CAPITAL ONE             4608
FIDELITY INVESTMENTS    4528
Name: SECONDARY_ENTITY_BUSINESS_NAME, type: <class 'float'>

CA    517753
TX    306873
NY    202901
WA    145738
NJ    134790
Name: WORKSITE_STATE, type: <class 'str'>

120000.0    36230
100000.0    32325
110000.0    30649
130000.0    28461
90000.0     28287
Name: WAGE_RATE_OF_PAY_FROM, type: <class 'numpy.float64'>

120000.0    15849
130000.0    13469
100000.0    13398
150000.0    13069
140000.0    12260
Name: WAGE_RATE_OF_PAY_TO, type: <class 'numpy.float64'>

Year         2394108
Hour          148881
Month           2299
Bi-Weekly        553
Week             548
Name: WAGE_UNIT_OF_PAY, type: <class 'str'>

2021    826305
2022    626084
2020    577334
2023    516668
Name: YEAR, type: <class 'numpy.int64'>

3    1018294
2     753801
1     411680
4     362616
Name: QUARTER, type: <class 'numpy.int64'>
"""

# To print the statistics
# for column in df.columns:
#     print(str(df[column].value_counts().head(5)).replace(
#         "dtype: int64",
#         "type: " + str(type(df[column][0]))
#     ))
#     print()


bot_PythonAgent.CODE_WITH_WRAPPERS = """\
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import savefig
import warnings
import pandas as pd

pd.set_option('display.max_columns', None)
warnings.simplefilter(action='ignore', category=pd.errors.DtypeWarning)

def save_image(filename):
    def decorator(func):
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
            savefig(filename)
        return wrapper
    return decorator

plt.show = save_image('image.png')(plt.show)
plt.savefig = save_image('image.png')(plt.savefig)

{code}
"""

bot_PythonAgent.SIMULATED_USER_SUFFIX_PROMPT = """
If there is an issue, you will fix the Python code.
Otherwise, provide a brief and concise comment, WITHOUT repeating the output.
"""


bot = PythonAgentBot()
bot.prompt_bot = "ChatGPT"
bot.code_iteration_limit = 3
bot.logit_bias = {
    "21362": -10,  # "!["
    "4380": 2,  # ("/
    "3478": 2,  # ('/
    "446": -2,  # ("
    "493": -2,  # ('
    "19701": -15,  # Sorry
    "10835": -5,  # Ap(ologies)
    "5159": -2,  # My (apologies, but I'm)
    "2170": -5,  # As (an AI language model)
    "31140": -10,  # Unfortunately
    "19173": -10,  # ' Unfortunately'
    "40": -10,  # I('m sorry)
    "663": -3,  # ']
    "7352": 2,  # '].
    "1473": 1,  # ':\n\n'
}
bot.allow_attachments = False


stub = Stub("poe-bot-quickstart")

image_bot = bot_PythonAgent.image_bot.copy_local_file("df.csv", "/root/df.csv")

bot_PythonAgent.image_exec = bot_PythonAgent.image_exec.copy_local_file(
    "df.csv", "df.csv"
)


@stub.function(image=image_bot)
@asgi_app()
def fastapi_app():
    app = make_app(bot, api_key=os.environ["POE_ACCESS_KEY"])
    return app
