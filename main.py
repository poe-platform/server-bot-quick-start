from fastapi_poe.samples.catbot import CatBot
from fastapi_poe import run

# Add your Poe API key here. You can go to https://poe.com/create_bot?api=1 to generate one.
POE_API_KEY = "meow" * 8

run(CatBot(), api_key=POE_API_KEY)