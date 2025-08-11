"""
Weather Bot for Poe - Provides weather information using OpenWeather API
"""

from __future__ import annotations
import asyncio
import json
from typing import AsyncIterable

import fastapi_poe as fp
from fastapi_poe.types import QueryRequest, SettingsRequest, SettingsResponse
from modal import Image, App, asgi_app


# OpenWeather API Configuration
OPENWEATHER_API_KEY = "18436a5aee03555399b6774854293b06"
OPENWEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5/weather"


class WeatherBot(fp.PoeBot):
    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[fp.PartialResponse]:
        """Handle user queries and return weather information"""
        
        user_message = request.query[-1].content.strip()
        
        # Check if user is asking for weather
        if not self._is_weather_request(user_message):
            yield fp.PartialResponse(
                text="Hi! I'm a weather bot. Ask me about the weather in any city! "
                     "For example: 'What's the weather in New York?' or 'Weather in London'"
            )
            return
        
        # Extract city name from the message
        city_name = self._extract_city_name(user_message)
        
        if not city_name:
            yield fp.PartialResponse(
                text="I couldn't find a city name in your message. "
                     "Please ask like: 'What's the weather in [city name]?'"
            )
            return
        
        # Get weather data
        try:
            weather_data = self._get_weather_data(city_name)
            response_text = self._format_weather_response(weather_data)
            yield fp.PartialResponse(text=response_text)
        except Exception as e:
            yield fp.PartialResponse(
                text=f"Sorry, I couldn't get weather information for '{city_name}'. "
                     f"Please check the city name and try again. Error: {str(e)}"
            )

    def _is_weather_request(self, message: str) -> bool:
        """Check if the message is asking for weather information"""
        weather_keywords = [
            'weather', 'temperature', 'temp', 'forecast', 'climate',
            'hot', 'cold', 'rain', 'sunny', 'cloudy', 'humidity'
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in weather_keywords)
    
    def _extract_city_name(self, message: str) -> str:
        """Extract city name from user message"""
        message_lower = message.lower()
        
        # Common patterns to look for
        patterns = [
            ' in ', ' for ', ' at ', ' of '
        ]
        
        city_name = ""
        
        # Look for patterns like "weather in New York"
        for pattern in patterns:
            if pattern in message_lower:
                parts = message_lower.split(pattern)
                if len(parts) > 1:
                    # Get the part after the pattern and clean it up
                    city_part = parts[1].strip()
                    # Remove common trailing words
                    city_part = city_part.replace('?', '').replace('.', '').replace('!', '')
                    # Take first few words as city name
                    city_words = city_part.split()[:3]  # Max 3 words for city name
                    city_name = ' '.join(city_words).strip()
                    break
        
        # If no pattern found, try to extract from the end of the message
        if not city_name:
            words = message.split()
            if len(words) >= 2:
                # Take last 1-2 words as potential city name
                city_name = ' '.join(words[-2:]).replace('?', '').replace('.', '').replace('!', '').strip()
        
        return city_name.title()  # Capitalize properly
    
    def _get_weather_data(self, city_name: str) -> dict:
        """Fetch weather data from OpenWeather API"""
        return get_weather_api_data(city_name, OPENWEATHER_API_KEY)
    
    def _format_weather_response(self, weather_data: dict) -> str:
        """Format weather data into a user-friendly response"""
        city = weather_data['name']
        country = weather_data['sys']['country']
        
        # Main weather info
        main = weather_data['main']
        weather = weather_data['weather'][0]
        wind = weather_data.get('wind', {})
        
        # Temperature
        temp = round(main['temp'])
        feels_like = round(main['feels_like'])
        temp_min = round(main['temp_min'])
        temp_max = round(main['temp_max'])
        
        # Convert to Fahrenheit for US users (optional)
        temp_f = round(temp * 9/5 + 32)
        feels_like_f = round(feels_like * 9/5 + 32)
        
        # Weather description
        description = weather['description'].title()
        
        # Additional info
        humidity = main['humidity']
        pressure = main['pressure']
        wind_speed = wind.get('speed', 0)
        
        # Format the response
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
        """Return bot settings"""
        return SettingsResponse(
            server_bot_dependencies={"requests": "2.31.0"}
        )


# Modal deployment setup
image = Image.debian_slim().pip_install("fastapi-poe==0.0.68", "requests==2.31.0")
app = App("weatherbot")

# Move imports inside the function to avoid Modal import issues
def get_weather_api_data(city_name: str, api_key: str) -> dict:
    """Helper function to fetch weather data"""
    import requests
    
    params = {
        'q': city_name,
        'appid': api_key,
        'units': 'metric'
    }
    
    response = requests.get("http://api.openweathermap.org/data/2.5/weather", params=params)
    
    if response.status_code == 404:
        raise Exception(f"City '{city_name}' not found")
    elif response.status_code == 401:
        raise Exception("API key is invalid")
    elif response.status_code != 200:
        raise Exception(f"API error: {response.status_code}")
    
    return response.json()


@app.function(image=image)
@asgi_app()
def fastapi_app():
    bot = WeatherBot()
    # Note: You'll need to replace these with your actual Poe bot credentials
    app = fp.make_app(bot, allow_without_key=True, access_key="vK0cjDYarSYZrhDry1K6eetf1Y8bNT9G")  # Temporary for testing
    return app