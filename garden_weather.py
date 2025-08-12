"""
Garden Weather Bot for Poe - Combines plant advice with weather information
"""

from __future__ import annotations

import os
from enum import Enum
from typing import AsyncIterable

import fastapi_poe as fp
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import App, Image, Secret, asgi_app


# ----------------------------------------
# Helper function to safely get API key
# ----------------------------------------
def get_openweather_api_key() -> str:
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OpenWeather API key not found in environment variables! "
            "Make sure you set it as a Modal secret."
        )
    return api_key


OPENWEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"


class UserState(Enum):
    GREETING = "greeting"
    EXPERIENCE_LEVEL = "experience_level"
    WATERING_PREFERENCE = "watering_preference"
    SUNLIGHT_PREFERENCE = "sunlight_preference"
    RECOMMENDATION = "recommendation"
    FOLLOW_UP = "follow_up"
    GENERAL = "general"


class GardenWeatherBot(fp.PoeBot):
    def __init__(self):
        super().__init__()
        # Simple state tracking (in production, you'd use a proper database)
        self.user_states = {}
        self.user_preferences = {}

        # Plant knowledge base
        self.easy_plants = {
            "low_water_low_sun": {
                "name": "Snake Plant",
                "description": "Sometimes called mother-in-law's tongue, this tough succulent grows well in just about any indoor space. Its upright, leathery, sword-shaped leaves are marbled with gray-green colors and may be edged with yellow or white.",
                "care": "Very forgiving if you forget to water it, and grows in low to medium light.",
            },
            "low_water_high_sun": {
                "name": "Jade Plant",
                "description": "An easy succulent with green, plump leaves and fleshy stems. This houseplant prefers bright light but can handle some shade.",
                "care": "Very forgiving if you forget to water it for a while, but doesn't appreciate overwatering. Can live for many decades!",
            },
            "high_water_low_sun": {
                "name": "Peace Lily",
                "description": "A low-maintenance indoor plant with glossy, lance-shaped leaves that arch gracefully. The white flowers are most common in summer.",
                "care": "Tolerates low light, low humidity, and inconsistent watering. Perfect for office spaces!",
            },
            "high_water_high_sun": {
                "name": "Money Plant",
                "description": "The shiny leaves look tropical and the slender trunk often comes braided. In Asia, these are thought to bring good fortune!",
                "care": "Easy to grow and does best with consistent water and bright light. A perfect prosperity plant!",
            },
        }

        self.advanced_plants = {
            "low_water_low_sun": {
                "name": "String of Pearls",
                "description": "A unique succulent with pearl-like leaves that cascade beautifully. Very Instagram-worthy!",
                "care": "Make sure soil is completely dry before watering, and keep in partial sun away from drafts.",
            },
            "low_water_high_sun": {
                "name": "Fiddle Leaf Fig",
                "description": "The Instagram star of houseplants! Large, violin-shaped leaves make a dramatic statement.",
                "care": "Needs plenty of humidity, indirect bright sunlight, moist soil, and infrequent waterings. Worth the challenge!",
            },
            "high_water_low_sun": {
                "name": "Maidenhair Fern",
                "description": "Delicate, lacy fronds that bring an elegant, ethereal quality to any space.",
                "care": "Loves misting, dappled light, and high humidity. A humid bathroom makes a perfect home!",
            },
            "high_water_high_sun": {
                "name": "Orchid",
                "description": "The ultimate flowering houseplant challenge! Beautiful, exotic blooms that are worth the effort.",
                "care": "Needs loose bark potting mix, indirect sunlight, high humidity, and careful watering. A true plant pro's prize!",
            },
        }

    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        user_message = request.query[-1].content.strip()
        user_id = request.user_id  # Use this to track user state

        # Check if it's a weather request
        if self._is_weather_request(user_message):
            async for response in self._handle_weather_request(user_message):
                yield response
            return

        # Handle gardening conversation flow
        current_state = self.user_states.get(user_id, UserState.GREETING)

        if current_state == UserState.GREETING:
            async for response in self._handle_greeting(user_id, user_message):
                yield response
        elif current_state == UserState.EXPERIENCE_LEVEL:
            async for response in self._handle_experience_level(user_id, user_message):
                yield response
        elif current_state == UserState.WATERING_PREFERENCE:
            async for response in self._handle_watering_preference(
                user_id, user_message
            ):
                yield response
        elif current_state == UserState.SUNLIGHT_PREFERENCE:
            async for response in self._handle_sunlight_preference(
                user_id, user_message
            ):
                yield response
        elif current_state == UserState.RECOMMENDATION:
            async for response in self._handle_recommendation_response(
                user_id, user_message
            ):
                yield response
        else:
            async for response in self._handle_general_chat(user_id, user_message):
                yield response

    async def _handle_greeting(
        self, user_id: str, message: str
    ) -> AsyncIterable[fp.PartialResponse]:
        """Handle initial greeting"""
        greeting = """🌱 Welcome to your Garden Weather Assistant! 🌦️

I'm here to help you find the perfect plant AND give you weather updates to keep your green friends happy!

Whether you're just starting your plant parent journey or you're already a seasoned plant pro, I've got recommendations that'll make your space bloom with joy! 🌸

Are you a **Newbie** to plants or a **Plant Pro**? If you're not sure, just let me know and I'll help you figure it out!

*Remember: I can also give you weather updates for your city - just ask about the weather anytime!* ☀️🌧️"""

        yield fp.PartialResponse(text=greeting)
        self.user_states[user_id] = UserState.EXPERIENCE_LEVEL

    async def _handle_experience_level(
        self, user_id: str, message: str
    ) -> AsyncIterable[fp.PartialResponse]:
        """Handle experience level selection"""
        message_lower = message.lower()

        if (
            "newbie" in message_lower
            or "beginner" in message_lower
            or "new" in message_lower
        ):
            self.user_preferences[user_id] = {"level": "newbie"}
            response = "Awesome! Every plant pro started as a newbie - you're planting the seeds of a beautiful journey! 🌱\n\nNow, let's talk watering - do you prefer plants that need **constant watering** or ones that **you can ignore** for a while? (Trust me, there's no wrong answer here!)"
            self.user_states[user_id] = UserState.WATERING_PREFERENCE
        elif (
            "pro" in message_lower
            or "experienced" in message_lower
            or "advanced" in message_lower
        ):
            self.user_preferences[user_id] = {"level": "pro"}
            response = "A seasoned plant parent! I love it! 🌿 You're ready to tackle some challenging beauties that'll really make your space shine.\n\nLet's dig into your preferences - do you prefer plants that need **constant attention with watering** or ones that are more **drought tolerant**?"
            self.user_states[user_id] = UserState.WATERING_PREFERENCE
        elif (
            "not sure" in message_lower
            or "don't know" in message_lower
            or "help" in message_lower
        ):
            response = """No worries! Let me help you figure it out! 🤔

**Newbie**: You're new to plants, want something forgiving, and prefer low-maintenance green friends that won't judge you if you forget to water them occasionally.

**Plant Pro**: You've successfully kept plants alive before, enjoy the challenge of caring for more demanding plants, and don't mind checking in on your green babies regularly.

Which sounds more like you?"""
            # Stay in the same state
        else:
            response = "I didn't quite catch that! Are you a **Newbie** or **Plant Pro**? Or would you like me to explain the difference? 🌱"
            # Stay in the same state

        yield fp.PartialResponse(text=response)

    async def _handle_watering_preference(
        self, user_id: str, message: str
    ) -> AsyncIterable[fp.PartialResponse]:
        """Handle watering preference"""
        message_lower = message.lower()

        if (
            "constant" in message_lower
            or "regular" in message_lower
            or "often" in message_lower
        ):
            self.user_preferences[user_id]["watering"] = "high"
            response = "Got it! You're ready to be a dedicated plant parent with regular watering duties! 💧\n\nNow for the sunshine question - will you put your plant in an area that gets **a lot of sun** or somewhere with **lower light**?"
        elif (
            "ignore" in message_lower
            or "forget" in message_lower
            or "low" in message_lower
            or "drought" in message_lower
        ):
            self.user_preferences[user_id]["watering"] = "low"
            response = "Perfect! Low-maintenance watering it is - your plant will be as chill as you are! 😎\n\nLast question - will your new green friend be living in an area that gets **a lot of sun** or somewhere with **lower light**?"
        else:
            response = "Let me rephrase that! Do you want a plant that needs **constant watering** (you check on it regularly) or one **you can ignore** for stretches of time? 💧"
            # Stay in the same state
            yield fp.PartialResponse(text=response)
            return

        self.user_states[user_id] = UserState.SUNLIGHT_PREFERENCE
        yield fp.PartialResponse(text=response)

    async def _handle_sunlight_preference(
        self, user_id: str, message: str
    ) -> AsyncIterable[fp.PartialResponse]:
        """Handle sunlight preference and provide recommendation"""
        message_lower = message.lower()

        if (
            "lot" in message_lower
            or "high" in message_lower
            or "bright" in message_lower
            or "yes" in message_lower
        ):
            self.user_preferences[user_id]["sunlight"] = "high"
        elif (
            "low" in message_lower
            or "little" in message_lower
            or "shade" in message_lower
            or "no" in message_lower
        ):
            self.user_preferences[user_id]["sunlight"] = "low"
        else:
            response = "Just to be clear - will your plant be in a spot with **lots of sun** or **lower light**? ☀️🌙"
            yield fp.PartialResponse(text=response)
            return

        # Generate recommendation
        preferences = self.user_preferences[user_id]
        level = preferences["level"]
        watering = preferences["watering"]
        sunlight = preferences["sunlight"]

        # Select plant database
        plant_db = self.easy_plants if level == "newbie" else self.advanced_plants

        # Create key for plant selection
        key = f"{watering}_water_{sunlight}_sun"
        selected_plant = plant_db[key]

        # Create recommendation with weather integration offer
        recommendation = f"""🌟 **Perfect! I've got the ideal plant for you!** 🌟

**Meet the {selected_plant['name']}!**

{selected_plant['description']}

**Why this plant is perfect for you:** {selected_plant['care']}

This beauty is going to thrive in your care! Plus, if you ever move it outdoors or want to know if natural rainfall will help with watering, just ask me about the weather in your city! 🌦️

**What do you think – are you interested in this plant?** 🤔"""

        self.user_states[user_id] = UserState.RECOMMENDATION
        yield fp.PartialResponse(text=recommendation)

    async def _handle_recommendation_response(
        self, user_id: str, message: str
    ) -> AsyncIterable[fp.PartialResponse]:
        """Handle user's response to plant recommendation"""
        message_lower = message.lower()

        if any(
            word in message_lower
            for word in ["yes", "interested", "love", "great", "perfect", "want"]
        ):
            response = """🎉 **Fantastic choice!** You're going to be such a great plant parent!

Here's a nugget of plant wisdom to get you started: *"The best time to plant was 20 years ago. The second best time is now!"* 🌱

**Pro tip:** Most houseplants prefer the same temperatures we do (60s-70s°F), but they don't handle dry air as well as we do. Keep them away from heaters and vents, and give them a light misting in winter when the air gets dry.

Happy planting! 🌿 And remember, I'm always here if you need weather updates for your green friends! ☀️🌧️"""

            self.user_states[user_id] = UserState.GENERAL
        else:
            # Provide alternative recommendation
            preferences = self.user_preferences[user_id]
            level = preferences["level"]

            # Get a different plant (simple rotation)
            plant_db = self.easy_plants if level == "newbie" else self.advanced_plants
            plants = list(plant_db.values())

            # Get the next plant in the list
            current_plant_name = None
            for key, plant in plant_db.items():
                if (
                    f"{preferences['watering']}_water_{preferences['sunlight']}_sun"
                    == key
                ):
                    current_plant_name = plant["name"]
                    break

            # Find alternative (just pick a different one for now)
            alternative = None
            for plant in plants:
                if plant["name"] != current_plant_name:
                    alternative = plant
                    break

            if alternative:
                response = f"""No worries! Let me suggest something different! 🔄

**How about the {alternative['name']}?**

{alternative['description']}

**Care requirements:** {alternative['care']}

This one might be more your style! **What do you think about this option?** 🌿"""
            else:
                response = "No problem! Let me know what specific qualities you're looking for in a plant, and I'll help you find the perfect green companion! 🌱"

        yield fp.PartialResponse(text=response)

    async def _handle_general_chat(
        self, user_id: str, message: str
    ) -> AsyncIterable[fp.PartialResponse]:
        """Handle general plant or weather questions"""
        message_lower = message.lower()

        plant_keywords = [
            "plant",
            "water",
            "care",
            "grow",
            "leaf",
            "soil",
            "pot",
            "garden",
        ]

        if any(keyword in message_lower for keyword in plant_keywords):
            response = """🌱 Great question! Here are some universal plant care tips:

• **Watering wisdom:** Stick your finger about an inch into the soil. If it's moist, wait a few days before watering!
• **Light logic:** Most houseplants prefer bright, indirect light rather than direct sunlight
• **Temperature tip:** Keep plants away from vents, heaters, and radiators
• **Humidity help:** Lightly mist your plants daily in winter when the air is driest

Want a specific plant recommendation? Just let me know your experience level and preferences!

And don't forget - I can also check the weather in your city if you want to know about rain for any outdoor plants! 🌦️"""
        else:
            response = """🌿 I'm here to help with plants and weather!

Ask me things like:
• "I'm a newbie looking for an easy plant"
• "What's the weather in [your city]?"
• "How do I care for houseplants?"
• "My plant leaves are turning yellow"

What can I help you with today? 🌱☀️"""

        yield fp.PartialResponse(text=response)

    # Weather functionality
    async def _handle_weather_request(
        self, message: str
    ) -> AsyncIterable[fp.PartialResponse]:
        """Handle weather requests"""
        city_name = self._extract_city_name(message)

        if not city_name:
            yield fp.PartialResponse(
                text="I couldn't find a city name in your message. Please ask like: 'What's the weather in [city name]?' 🌦️"
            )
            return

        try:
            weather_data = self._get_weather_data(city_name)
            response_text = self._format_weather_response(weather_data)
            yield fp.PartialResponse(text=response_text)
        except Exception as e:
            yield fp.PartialResponse(
                text=f"Sorry, I couldn't get weather information for '{city_name}'. Please check the city name and try again! 🌧️"
            )

    def _is_weather_request(self, message: str) -> bool:
        """Check if the message is asking for weather information"""
        weather_keywords = [
            "weather",
            "temperature",
            "temp",
            "forecast",
            "climate",
            "hot",
            "cold",
            "rain",
            "sunny",
            "cloudy",
            "humidity",
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in weather_keywords)

    def _extract_city_name(self, message: str) -> str:
        """Extract city name from user message"""
        message_lower = message.lower()
        patterns = [" in ", " for ", " at ", " of "]
        city_name = ""

        for pattern in patterns:
            if pattern in message_lower:
                parts = message_lower.split(pattern)
                if len(parts) > 1:
                    city_part = parts[1].strip()
                    city_part = (
                        city_part.replace("?", "").replace(".", "").replace("!", "")
                    )
                    city_words = city_part.split()[:3]
                    city_name = " ".join(city_words).strip()
                    break

        if not city_name:
            words = message.split()
            if len(words) >= 2:
                city_name = (
                    " ".join(words[-2:])
                    .replace("?", "")
                    .replace(".", "")
                    .replace("!", "")
                    .strip()
                )

        return city_name.title()

    def _get_weather_data(self, city_name: str) -> dict:
        """Fetch weather data from OpenWeather API"""
        return get_weather_api_data(city_name, get_openweather_api_key())

    def _format_weather_response(self, weather_data: dict) -> str:
        """Format weather data with plant care tips"""
        city = weather_data["name"]
        country = weather_data["sys"]["country"]

        main = weather_data["main"]
        weather = weather_data["weather"][0]
        wind = weather_data.get("wind", {})

        temp = round(main["temp"])
        feels_like = round(main["feels_like"])
        temp_min = round(main["temp_min"])
        temp_max = round(main["temp_max"])

        temp_f = round(temp * 9 / 5 + 32)
        feels_like_f = round(feels_like * 9 / 5 + 32)

        description = weather["description"].title()
        humidity = main["humidity"]
        pressure = main["pressure"]
        wind_speed = wind.get("speed", 0)

        # Add plant care advice based on weather
        plant_advice = self._get_plant_advice_from_weather(weather_data)

        response = f"""🌤️ **Weather in {city}, {country}**

📊 **Current Conditions:**
• Temperature: {temp}°C ({temp_f}°F)
• Feels like: {feels_like}°C ({feels_like_f}°F)
• Condition: {description}
• High/Low: {temp_max}°C / {temp_min}°C

💨 **Additional Details:**
• Humidity: {humidity}%
• Pressure: {pressure} hPa
• Wind Speed: {wind_speed} m/s

🌱 **Plant Care Tip Based on Today's Weather:**
{plant_advice}"""

        return response

    def _get_plant_advice_from_weather(self, weather_data: dict) -> str:
        """Generate plant care advice based on current weather"""
        description = weather_data["weather"][0]["description"].lower()
        temp = weather_data["main"]["temp"]
        humidity = weather_data["main"]["humidity"]

        if "rain" in description or "drizzle" in description:
            return "🌧️ It's rainy! Perfect time to skip watering outdoor plants - Mother Nature's got this covered! Indoor plants might appreciate the extra humidity though."
        elif "snow" in description:
            return "❄️ Snow day! Keep your outdoor plants protected and bring any tender potted plants inside. Indoor plants might need extra humidity due to heating."
        elif temp > 30:  # Very hot
            return "🔥 Hot weather alert! Your plants will be extra thirsty today. Check soil moisture frequently and provide shade for sensitive plants."
        elif temp < 5:  # Very cold
            return "🥶 Chilly weather! Protect your outdoor plants from frost and keep indoor plants away from cold windows and drafts."
        elif humidity < 30:
            return "🏜️ Low humidity today! Your indoor plants would love a gentle misting, and outdoor plants might need extra water."
        elif humidity > 80:
            return "💧 High humidity today! Great for your plants' happiness! You might be able to water less frequently."
        elif "clear" in description or "sunny" in description:
            return "☀️ Beautiful sunny day! Perfect weather for your plants to photosynthesize. Check that they're not getting too much direct sun though!"
        else:
            return "🌤️ Lovely weather for plants today! A good day to check on your green friends and see how they're doing."

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        """Return bot settings"""
        return SettingsResponse()


# Modal deployment setup
image = Image.debian_slim().pip_install("fastapi-poe==0.0.68", "requests==2.31.0")
app = App("garden-weather-bot")


def get_weather_api_data(city_name: str, api_key: str) -> dict:
    """Helper function to fetch weather data"""
    import requests

    params = {"q": city_name, "appid": api_key, "units": "metric"}

    response = requests.get(OPENWEATHER_BASE_URL, params=params)

    if response.status_code == 404:
        raise Exception(f"City '{city_name}' not found")
    elif response.status_code == 401:
        raise Exception("API key is invalid")
    elif response.status_code != 200:
        raise Exception(f"API error: {response.status_code}")

    return response.json()


@app.function(image=image, secrets=[Secret.from_name("OPENWEATHER_API_KEY")])
@asgi_app()
def fastapi_app():
    bot = GardenWeatherBot()
    # You'll need to replace this with your actual Poe bot credentials
    return fp.make_app(bot, allow_without_key=True)  # Change for production
