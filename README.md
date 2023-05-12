# Heroku Poe sample

This is a sample repository for creating Poe API bots on Heroku. For more information on
API bots, see [poe-protocol](https://github.com/poe-platform/poe-protocol).

## Getting started

- Create an account on [heroku.com](https://heroku.com)
- On the website, create a new application. Let's name it $YOUR_APP
- [Install](https://devcenter.heroku.com/articles/heroku-cli#install-the-heroku-cli) the
  Heroku CLI
- Open the [bot creation page](https://poe.com/create_bot?api=1). An API key will be
  pre-generated for you.
- Open a terminal and run:
  - `git clone https://github.com/poe-platform/heroku-sample.git`
  - `cd heroku-sample`
  - `heroku git:remote -a $YOUR_APP`
  - `heroku config:set POE_API_KEY=$POE_API_KEY`, where `$POE_API_KEY` is the API key
    you got from [bot creation page](https://poe.com/create_bot?api=1)
  - `git push heroku main`
- Now your app should be online at `https://$YOUR_APP.herokuapp.com/`
- Add the URL in the bot creation page
- Hit "Create bot"
- Now your bot is live!

## Customize your bot

The above instructions just start a simple bot with no AI capabilities. To make your own
bot, modify `main.py` and push to Heroku again. You can see sample code in the
[poe-protocol](https://github.com/poe-platform/poe-protocol) repository or on
[Replit](https://replit.com/@JelleZijlstra2/Poe-API-Template).
