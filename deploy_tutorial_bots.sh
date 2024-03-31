# Script to deploy tutorial bots
# You need to change the bot handle

# poe.com/EchoBotDemonstration
BOT_NAME="EchoBotDemonstration"; modal deploy --name $BOT_NAME echobot.py

# poe.com/CatBotDemo
BOT_NAME="CatBotDemo"; modal deploy --name $BOT_NAME catbot/__init__.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

# poe.com/AllCapsBotDemo
BOT_NAME="AllCapsBotDemo"; modal deploy --name $BOT_NAME turbo_allcapsbot.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

# poe.com/ImageResponseBotDemo
BOT_NAME="ImageResponseBotDemo"; modal deploy --name $BOT_NAME image_response_bot.py

# poe.com/PDFCounterBotDemo
BOT_NAME="PDFCounterBotDemo"; modal deploy --name $BOT_NAME pdf_counter_bot.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

# poe.com/FunctionCallingDemo
BOT_NAME="FunctionCallingDemo"; modal deploy --name $BOT_NAME function_calling_bot.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY

# poe.com/TurboVsClaudeBotDemo
BOT_NAME="TurboVsClaudeBotDemo"; modal deploy --name $BOT_NAME turbo_vs_claude.py; curl -X POST https://api.poe.com/bot/fetch_settings/$BOT_NAME/$POE_ACCESS_KEY
