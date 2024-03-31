"""

Helper function to execute Python code

modal deploy function_exec.py
"""

import sys
from io import StringIO

from modal import Image, Stub

image = Image.debian_slim().pip_install(
    "fastapi-poe==0.0.23",
    "huggingface-hub==0.16.4",
    "ipython",
    "scipy",
    "matplotlib",
    "scikit-learn",
    "pandas==1.3.2",
    "ortools",
    "torch",
    "torchvision",
    "tensorflow",
    "spacy",
    "transformers",
    "opencv-python-headless",
    "nltk",
    "openai",
    "requests",
    "beautifulsoup4",
    "newspaper3k",
    "feedparser",
    "sympy",
    "tensorflow",
    "cartopy",
    "wordcloud",
    "gensim",
    "keras",
    "librosa",
    "XlsxWriter",
    "docx2txt",
    "markdownify",
    "pdfminer.six",
    "Pillow",
    "opencv-python",
    "sortedcontainers",
    "intervaltree",
    "geopandas",
    "basemap",
    "tiktoken",
    "basemap-data-hires",
    "yfinance",
    "dill",
)

stub = Stub("poe-bot-quickstart")


@stub.function(image=image, timeout=30)
def execute_code(code):
    import traitlets.config
    from IPython.terminal.embed import InteractiveShellEmbed

    config = traitlets.config.Config()
    config.InteractiveShell.colors = "NoColor"
    # config.PlainTextFormatter.max_width = 40  # not working
    # config.InteractiveShell.width = 40  # not working
    ipython = InteractiveShellEmbed(config=config)

    # Redirect stdout temporarily to capture the output of the code snippet
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    # Execute the code with the silent parameter set to True
    _ = ipython.run_cell(code, silent=True, store_history=False, shell_futures=False)

    # Restore the original stdout and retrieve the captured output
    captured_output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    return captured_output
