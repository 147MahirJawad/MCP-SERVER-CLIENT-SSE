from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient
from dotenv import load_dotenv
from typing import Dict, List
from fastapi import Request
from fastapi.responses import StreamingResponse
import os
import requests
import asyncio

# Load environment variables
load_dotenv()

# Initialize MCP server with FastAPI
PORT = int(os.environ.get("PORT", 8001))
mcp = FastMCP("multi-tool-server", host="0.0.0.0", port=PORT)

# Tavily client setup
if "TAVILY_API_KEY" not in os.environ:
    raise Exception("TAVILY_API_KEY environment variable not set")
tavily_client = TavilyClient(os.environ["TAVILY_API_KEY"])

@mcp.tool()
def web_search(query: str) -> List[Dict]:
    """Search the web using Tavily"""
    try:
        response = tavily_client.search(query)
        return response["results"]
    except Exception as e:
        return {"error": str(e)}

# Weather API setup
if "WEATHERAPI_KEY" not in os.environ:
    raise Exception("WEATHERAPI_KEY environment variable not set")

@mcp.tool()
def get_weather(location: str, days: int = 1, aqi: bool = False) -> Dict:
    """Fetch weather data for a given location"""
    try:
        if not isinstance(location, str) or not location.strip():
            raise ValueError("Location must be a non-empty string")

        endpoint = "forecast.json" if days > 1 else "current.json"
        response = requests.get(
            f"https://api.weatherapi.com/v1/{endpoint}",
            params={
                "key": os.environ["WEATHERAPI_KEY"],
                "q": location,
                "days": days,
                "aqi": "yes" if aqi else "no"
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise ValueError(data["error"].get("message", "Unknown error"))

        return {
            "status": "success",
            "data": {
                "location": data["location"]["name"],
                "temperature": data["current"]["temp_c"],
                "condition": data["current"]["condition"]["text"],
                "humidity": data["current"]["humidity"],
                "wind": f"{data['current']['wind_kph']} km/h",
                "last_updated": data["current"]["last_updated"]
            }
        }

    except requests.exceptions.RequestException as e:
        return {"status": "error", "error_type": "network_error", "message": str(e)}
    except ValueError as e:
        return {"status": "error", "error_type": "validation_error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "error_type": "unexpected_error", "message": str(e)}

@mcp.tool()
def add_integers(num1: int, num2: int) -> Dict:
    """Add two positive integers"""
    if num1 < 0 or num2 < 0:
        return {"error": "Both integers must be positive"}
    return {"result": num1 + num2}


# Run MCP with SSE support
if __name__ == "__main__":
    mcp.settings.port = PORT
    mcp.run(transport="sse")
