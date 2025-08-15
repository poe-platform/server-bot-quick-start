"""
Weather Bot for Poe - Provides weather information using OpenWeather API
"""

from __future__ import annotations

import os
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
            "Make sure you set it as a Modal secret with:\n"
            "modal secret set OPENWEATHER_API_KEY YOUR_API_KEY"
        )
    return api_key


OPENWEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"


class WeatherBot(fp.PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        user_message = request.query[-1].content.strip()

        if not self._is_weather_request(user_message):
            yield fp.PartialResponse(
                text="Hi! I'm a weather bot. Ask me about the weather in any city! "
                "For example: 'What's the weather in New York?' or 'Weather in London'"
            )
            return

        city_name = self._extract_city_name(user_message)

        if not city_name:
            yield fp.PartialResponse(
                text="I couldn't find a city name in your message. "
                "Please ask like: 'What's the weather in [city name]?'"
            )
            return

        try:
            weather_data = self._get_weather_data(city_name)
            response_text = self._format_weather_response(weather_data)
            yield fp.PartialResponse(text=response_text)
        except Exception:
            yield fp.PartialResponse(
                text=f"Sorry, I couldn't get weather information for '{city_name}'. "
                f"Please check the city name and try again."
            )

    def _is_weather_request(self, message: str) -> bool:
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
        return get_weather_api_data(city_name, get_openweather_api_key())

    def _format_weather_response(self, weather_data: dict) -> str:
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

        response = f"""🌤️ **Weather in {city}, {country}**

📊 **Current Conditions:**
• Temperature: {temp}°C ({temp_f}°F)
• Feels like: {feels_like}°C ({feels_like_f}°F)
• Condition: {description}
• High/Low: {temp_max}°C / {temp_min}°C

💨 **Additional Details:**
• Humidity: {humidity}%
• Pressure: {pressure} hPa
• Wind Speed: {wind_speed} m/s"""

        return response

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        return SettingsResponse(server_bot_dependencies={"requests": "2.31.0"})


# Modal deployment setup
image = Image.debian_slim().pip_install("fastapi-poe==0.0.68", "requests==2.31.0")
app = App("weatherbot")


def get_weather_api_data(city_name: str, api_key: str) -> dict:
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
    bot = WeatherBot()
    # Remove allow_without_key for production security
    return fp.make_app(bot, access_key="vK0cjDYarSYZrhDry1K6eetf1Y8bNT9G")
