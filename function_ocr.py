"""

Helper function to OCR

modal deploy function_ocr.py
"""

import os

import requests
from modal import Image, Stub

image = Image.debian_slim().apt_install("wget").pip_install("nougat-ocr==0.1.14")

stub = Stub("poe-bot-quickstart")


@stub.function(image=image, timeout=180)
def nougat_ocr(url):
    local_filename = "downloaded.pdf"

    r = requests.get(url)

    with open(local_filename, "wb") as f:
        f.write(r.content)

    # not sure if I really need to chain them
    os.system(
        f"wget -O {local_filename} {url} && nougat {local_filename} --out output --pages 1"
    )

    with open("output/downloaded.mmd") as f:
        output = f.read()

    return output
