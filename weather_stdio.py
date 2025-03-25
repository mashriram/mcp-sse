# weather_stdio.py (Modified for Diagnostics)

from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import asyncio
import json
import sys  # Import sys


# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""


@mcp.tool()
async def get_alerts(state: str, session_id:str = "") -> str: # Modified function signature
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    print(f"get_alerts called with state={state}, session_id={session_id}", file=sys.stderr)  # Log to stderr

    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    result_string = "\n---\n".join(alerts)
    print(f"get_alerts result: {result_string}", file=sys.stderr)  # Log result
    return result_string

@mcp.tool()
async def get_forecast(latitude: float, longitude: float, session_id: str = "") -> str: # Modified
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    print(f"get_forecast called with latitude={latitude}, longitude={longitude}, session_id={session_id}", file=sys.stderr)  # Log

    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    result_string = "\n---\n".join(forecasts)
    print(f"get_forecast result: {result_string}", file=sys.stderr)  # Log result
    return result_string



async def main(): # Create main
    reader = asyncio.StreamReader() # StreamReader
    protocol = asyncio.StreamReaderProtocol(reader) # Stream Reader

    # Ensure it uses std.in
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    while True:
        request = await reader.readline()
        if not request:
            print("No request found", file=sys.stderr)
            break
        try:
            tool_request = json.loads(request)
            tool_args = tool_request.get('arguments', {})
            if "session_id" in tool_request:
                tool_args["session_id"] = tool_request["session_id"]

            if tool_request.get("tool_name") == 'get_forecast':
                results = await get_forecast(**tool_args)
                print("results: ", results)
            elif tool_request.get("tool_name") == "get_alerts":
                results = await get_alerts(**tool_args)
                print("results", results)

            if results:
                sys.stdout.write(json.dumps({"result": results}) + "\n")
                sys.stdout.flush() #ENSURE TO WRITE TO STDOUT
        except json.JSONDecodeError:
            print("Bad request found")
            sys.stderr.write("Invalid JSON received\n")

if __name__ == "__main__":
    # No mcp.run is happening
    asyncio.run(main())