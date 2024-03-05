# Poe server bot quick start

Welcome to the Poe server bot quick start. This repository serves as a companion to our
[tutorial](https://creator.poe.com/docs/quick-start) and contains starter code that
allows you to quickly get a bot running. The following are some of the examples included
in this repo. Note that the starter code assumes you have Modal setup for deployment
(the instructions for which are described in the aforementioned
[tutorial](https://creator.poe.com/docs/quick-start))

### EchoBot

This bot simply repeats the user's query in the response and provides a good starting
point to build any type of bot. To deploy, run `modal deploy echobot.py`

A correct implementation would look like https://poe.com/EchoBotDemonstration

### TurboAllCapsBot

- This bot responds to the user's query using GPT-3.5-Turbo. It demonstrates how to use
  the Poe platform to cover the inference costs for your chatbot. To deploy, run
  `modal deploy turbo_allcapsbot.py`.
- Before you are able to use the bot, you also need to synchronize the bot's settings
  with the Poe Platform, the instructions for which are specified
  [here](https://creator.poe.com/docs/updating-bot-settings).

A correct implementation would look like https://poe.com/AllCapsBotDemo

### CatBot

A sample bot that demonstrates the Markdown capabilities of the Poe API. To deploy, run
`modal deploy catbot/__init__.py`

A correct implementation would look like https://poe.com/CatBotDemo

### ImageResponseBot

A bot that demonstrates how to render an image in the response using Markdown. To
deploy, run `modal deploy image_response_bot.py`

A correct implementation would look like https://poe.com/ImageResponseBotDemo

### PDFCounterBot

- A bot that demonstrates how to enable file upload for the users of your bot.
- Before you are able to use the bot, you also need to synchronize the bot's settings
  with the Poe Platform, the instructions for which are specified
  [here](https://creator.poe.com/docs/updating-bot-settings).
- To deploy, run `modal deploy pdf_counter_bot.py`

A correct implementation would look like https://poe.com/PDFCounterBotDemo

### VideoBot

- A bot that demonstrates how to attach files to your bot response. This example
  specifically uses video, but outputting other file types is fairly similar.
- Before you are able to use this bot, you do need to set your access key. You can get
  yours from the [create bot page](https://poe.com/create_bot?server=1).
- To deploy, run `modal deploy video_bot.py`

### Function calling bot

- A bot that demonstrates how to use the Poe API for function calling.
- Before you are able to use the bot, you also need to synchronize the bot's settings
  with the Poe Platform, the instructions for which are specified
  [here](https://creator.poe.com/docs/updating-bot-settings).
- To deploy, run `modal deploy function_calling_bot.py`

### HttpRequestBot

Provides an example of how to access HTTP request information in your bot. To deploy,
run `modal deploy http_request_bot.py`

### HuggingFaceBot

Provides an example of a bot powered by a model hosted on HuggingFace. To deploy, run
`modal deploy huggingface_bot.py`

### Langchain OpenAI

Provides an example of a bot powered by Langchain. This bot requires you to provide your
OpenAI key. To deploy, run `modal deploy langchain_openai.py`

### TurboVsClaudeBot

- This is a more advanced example that demonstrates how to render output in realtime
  comparing two different bots. To deploy, run `modal deploy turbo_vs_claude.py`
- Before you are able to use the bot, you also need to synchronize the bot's settings
  with the Poe Platform, the instructions for which are specified
  [here](https://creator.poe.com/docs/updating-bot-settings).

A correct implementation would look like https://poe.com/TurboVsClaudeBotDemo
