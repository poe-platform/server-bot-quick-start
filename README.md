# Poe server bot quick start

Welcome to the Poe server bot quick start.

This repository serves as a companion to our
[tutorial](https://creator.poe.com/docs/quick-start) and contains starter code that
allows you to quickly get a bot running. The following are some of the examples included
in this repo.

Note that the starter code assumes you have Modal setup for deployment (the instructions
for which are described in the aforementioned
[tutorial](https://creator.poe.com/docs/quick-start)).

### EchoBot

- This bot simply repeats the user's query in the response.
- Before you build any server bots, you should start with reproducing this bot.
- This will ensure that your have a working fastapi_poe and modal setup.
- To deploy, run `modal deploy echobot.py`

A correct implementation would look like https://poe.com/EchoBotDemo

### PromptBot

- This bot is an implementation of the prompt bot as a server bot.
- It demonstrates how to use the Poe platform to cover the inference costs for your
  chatbot.
- This bot uses Claude-3-Haiku and the system prompt instructs the bot to produce
  Haikus.
- If you intend to call Poe server to build your bot response, you should check if you
  can reproduce this bot.
- To deploy, run `modal deploy prompt_bot.py`
- Before you are able to use the bot, you also need to synchronize the bot's settings
  with the Poe Platform, the instructions for which are specified
  [here](https://creator.poe.com/docs/server-bots-functional-guides#updating-bot-settings).

A correct implementation would look like https://poe.com/PromptBotDemo

### WrapperBot

- This bot is an implementation of the prompt bot as a server bot, but your own model
  provider API key.
- It demostrates how to wrap OpenAI API.
- You will need your OpenAI API key.
- To deploy, run `modal deploy wrapper_bot.py`

A correct implementation would look like https://poe.com/WrapperBotDemo

### SDXLBot

- This bot demonstrates how to wrap an image generation endpoint.
- It uses Fireworks AI's StableDiffusionXL endpoint. You will need to provide your own
  key for this.
- Alternatively, you can change the URL to point at a different provider or model.
- To deploy, run `modal deploy sdxl_bot.py`

A correct implementation would look like https://poe.com/StableDiffusionXL

### CatBot

- A sample bot that demonstrates the Markdown capabilities of the Poe API.
- See instructions [here](./catbot.md).
- To deploy, run `modal deploy catbot.py`

A correct implementation would look like https://poe.com/CatBotDemo

### ImageResponseBot

- A bot that demonstrates how to render an image in the response using Markdown.
- To deploy, run `modal deploy image_response_bot.py`

A correct implementation would look like https://poe.com/ImageResponseBotDemo

### VideoBot

- A bot that demonstrates how to attach files to your bot response. This example
  specifically uses video, but outputting other file types is fairly similar.
- To deploy, run `modal deploy video_bot.py`
- Before you are able to use the bot, you also need to synchronize the bot's settings
  with the Poe Platform, the instructions for which are specified
  [here](https://creator.poe.com/docs/server-bots-functional-guides#updating-bot-settings).

A correct implementation would look like https://poe.com/VideoBotDemo

### PDFCounterBot

- A bot that demonstrates how to enable file upload for the users of your bot.
- To deploy, run `modal deploy pdf_counter_bot.py`
- Before you are able to use the bot, you also need to synchronize the bot's settings
  with the Poe Platform, the instructions for which are specified
  [here](https://creator.poe.com/docs/server-bots-functional-guides#updating-bot-settings).

A correct implementation would look like https://poe.com/PDFCounterBotDemo

### FunctionCallingBot

- A bot that demonstrates how to use the Poe API for function calling.
- To deploy, run `modal deploy function_calling_bot.py`
- Before you are able to use the bot, you also need to synchronize the bot's settings
  with the Poe Platform, the instructions for which are specified
  [here](https://creator.poe.com/docs/server-bots-functional-guides#updating-bot-settings).

A correct implementation would look like https://poe.com/FunctionCallingDemo

### LogBot

- Illustrate what is contained in the QueryRequest object.
- To deploy, run `modal deploy log_bot.py`

A correct implementation would look like https://poe.com/LogBotDemo

### HTTPRequestBot

- Provides an example of how to access HTTP request information in your bot.
- To deploy, run `modal deploy http_request_bot.py`

A correct implementation would look like https://poe.com/HTTPRequestBotDemo

### TurboAllCapsBot

- This bot responds to the user's query using GPT-3.5-Turbo.
- It demonstrates how to use the Poe platform to cover the inference costs for your
  chatbot.
- To deploy, run `modal deploy turbo_allcapsbot.py`.
- Before you are able to use the bot, you also need to synchronize the bot's settings
  with the Poe Platform, the instructions for which are specified
  [here](https://creator.poe.com/docs/server-bots-functional-guides#updating-bot-settings).

A correct implementation would look like https://poe.com/AllCapsBotDemo

### TurboVsClaudeBot

- This is a more advanced example that demonstrates how to render output in realtime
  comparing two different bots.
- To deploy, run `modal deploy turbo_vs_claude.py`
- Before you are able to use the bot, you also need to synchronize the bot's settings
  with the Poe Platform, the instructions for which are specified
  [here](https://creator.poe.com/docs/server-bots-functional-guides#updating-bot-settings).

A correct implementation would look like https://poe.com/TurboVsClaudeBotDemo
