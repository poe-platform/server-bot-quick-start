# How to Create Your Own Poe Server Bot
*A step-by-step guide*

## What You're Building
You'll create a **server bot** - a custom AI chatbot that runs your own code and can do things regular Poe bots can't, like remember conversations, connect to websites, or process data in unique ways.

**Server Bot vs Regular Bot:**
- **Regular Bot**: Just a prompt that Poe runs
- **Server Bot**: Your own code running on a server that Poe connects to

**Why Modal?** Modal runs your Python code in the cloud 24/7, so your bot works without keeping your computer on.

---

## Step 1: Project Setup

### Get the Template Code
In your terminal, run these commands:
```bash
git clone https://github.com/poe-platform/server-bot-quick-start
cd server-bot-quick-start
pip3 install -r requirements.txt
```

*What this does: Downloads example bot code and installs the tools you need*

### Choose Your Starting Point
The folder contains several example bots. For your custom bot, you can either:
- **Start simple**: Modify `echobot.py` (just repeats what users say)
- **Start advanced**: Copy one of the other examples that's closer to what you want

### Create Your Custom Bot
1. **Copy an example**: `cp echobot.py my_bot.py`
2. **Open in your editor**: Open `my_bot.py` in VS Code, Sublime, or any text editor
3. **Customize the logic**: Find the `get_response` method and change what your bot does

**Basic customization example:**
```python
async def get_response(self, query: QueryRequest) -> AsyncIterable[fp.PartialResponse]:
    user_message = query.query[-1].content
    
    # Replace this echo logic with YOUR bot's logic
    if "hello" in user_message.lower():
        response = "Hi there! I'm your custom bot."
    elif "help" in user_message.lower():
        response = "I can help with [YOUR BOT'S SPECIFIC FEATURES]"
    else:
        response = f"Interesting! You said: {user_message}"
    
    yield fp.PartialResponse(text=response)
```

---

## Step 2: Deploying Your Bot

### Install Modal
```bash
pip3 install modal
```

### Setup Modal Access
Run this command (you only do this once):
```bash
modal token new --source poe
```

*What happens: Opens your browser to connect your terminal to Modal with your GitHub account*

### Deploy Your Bot
From the `server-bot-quick-start` directory, run:
```bash
modal serve my_bot.py
```

*What this does: Runs your bot temporarily for testing. Look for a URL like:*
```
https://yourname--my-bot-fastapi-app-dev.modal.run
```

**Copy this URL** - you'll need it next!

---

## Step 3: Connect to Poe

### Create Your Poe Bot
1. Go to [poe.com/create_bot](https://poe.com/create_bot)
2. Select **"Server bot"**
3. Fill out the form:
   - **Bot Name**: Choose something descriptive
   - **Server URL**: Paste your URL from Step 2
   - **Description**: Explain what your bot does
4. Click **"Create Bot"**

**Important:** Copy down the **Bot Name** and **Access Key** that appear!

### Configure Your Credentials
1. Open your `my_bot.py` file
2. Find this line near the bottom:
   ```python
   app = fp.make_app(bot, allow_without_key=True)
   ```
3. Replace it with:
   ```python
   app = fp.make_app(bot, access_key="YOUR_ACCESS_KEY", bot_name="YOUR_BOT_NAME")
   ```
4. Replace with your actual values from Poe
5. Save the file

*What this does: Securely connects your code to your Poe bot*

### Test Your Bot
Modal automatically updates when you save. Go to Poe and try talking to your bot!

---

## Step 4: Make It Permanent

When your bot is working correctly:

### Deploy for Production
```bash
modal deploy my_bot.py
```

*What this does: Makes your bot run 24/7 instead of just while testing*

### Update Your Poe Bot
1. Copy the new permanent URL (won't have `-dev` in it)
2. Go to your Poe bot settings
3. Update the **Server URL** with the permanent URL
4. Click **"Run check"** to verify it works

---

## Customizing Your Bot

### Add Conversation Memory
```python
class MyBot(fp.PoeBot):
    def __init__(self):
        super().__init__()
        self.conversations = {}  # Remember what users said
```

### Connect to Free APIs
Add real-world data to make your bot more useful:

**Weather APIs:**
- OpenWeatherMap (free tier): Current weather for any city
- WeatherAPI: Weather forecasts and conditions

**Location & Maps:**
- Nominatim (OpenStreetMap): Convert addresses to coordinates
- REST Countries: Country information and data

**Transportation:**
- OpenTripPlanner: Public transit directions
- Overpass API: Real-time map data

**Useful Data:**
- JSONPlaceholder: Fake data for testing
- REST Countries: Country facts and statistics  
- Dog CEO API: Random dog pictures
- JokeAPI: Programming and general jokes

**Example API call in your bot:**
```python
import httpx  # Add this import at the top

async def get_response(self, query: QueryRequest) -> AsyncIterable[fp.PartialResponse]:
    user_message = query.query[-1].content
    
    if "dog" in user_message.lower():
        async with httpx.AsyncClient() as client:
            response = await client.get("https://dog.ceo/api/breeds/image/random")
            data = response.json()
            bot_response = f"Here's a random dog! {data['message']}"
        yield fp.PartialResponse(text=bot_response)
```

### Smart Responses
```python
# Check for multiple conditions
if "math" in user_message and any(op in user_message for op in ["+", "-", "*", "/"]):
    # Do math
elif user_message.endswith("?"):
    # Handle questions differently
elif len(user_message.split()) > 10:
    # Handle long messages
```

---

## Common Issues

**"Command not found" for modal**: Make sure pip3 installed correctly

**Bot not responding on Poe**: Check your access key and bot name are exact matches

**Changes not showing**: Save your file - Modal auto-updates

**URL stopped working**: Redeploy and update the Server URL in Poe settings

---

## Next Steps

Once your basic bot works:

1. **Add unique features** that make your bot special
2. **Handle edge cases** (what if users say unexpected things?)
3. **Test thoroughly** with friends before sharing widely
4. **Iterate based on feedback** from real users

### Advanced Features to Explore
- File upload processing
- Calling other Poe bots from your bot
- Database integration
- Complex conversation flows
- API integrations

---

## Resources
- [Poe Documentation](https://creator.poe.com/docs)
- [Modal Documentation](https://modal.com/docs)
- [fastapi-poe Library](https://pypi.org/project/fastapi-poe/)

Your server bot is now live and running in the cloud! 🎉