# groq_client_middleware.py
import asyncio
import aiohttp
import json
import urllib.parse  # No longer need uuid on the client
from typing import Optional

async def sse_client(url: str, message_queue: asyncio.Queue):
    """
    Connects to an SSE endpoint, retrieves the session ID and messages endpoint,
    and listens for messages.

    Args:
        url: The URL of the SSE endpoint (e.g., "http://0.0.0.0:8080/sse").
        message_queue: An asyncio.Queue to put received messages on.
    """
    session_id: Optional[str] = None
    messages_url: Optional[str] = None
    endpoint_found = False  # Flag to indicate if endpoint has been found
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    print("SSE connection established.")
                    async for line in response.content.iter_any():
                        if line:
                            try:
                                decoded_line = line.decode('utf-8').strip()
                                if decoded_line.startswith("event: endpoint") and not endpoint_found:
                                    endpoint_found = True
                                    try:
                                        # Parse the JSON data directly from the line
                                        data_part = decoded_line.split("data: ", 1)[1]
                                        endpoint_data = json.loads(data_part)
                                        messages_url = endpoint_data["messages_url"]

                                        parsed_url = urllib.parse.urlparse(messages_url)
                                        query_params = urllib.parse.parse_qs(parsed_url.query)
                                        session_id = query_params.get("session_id", [None])[0]

                                        if not session_id:
                                            print("Warning: session_id missing from endpoint data")

                                        print(f"Retrieved messages endpoint: {messages_url} and session_id: {session_id}")

                                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                                        print(f"Error decoding endpoint data: {e=}")  # Use e= for clearer debugging
                                        # Consider *not* continuing if endpoint data is bad
                                        continue  # Skip to the next line

                                elif decoded_line.startswith("data:") and endpoint_found:
                                    data = decoded_line[5:].strip()  # Remove "data:" prefix
                                    try:
                                        message = json.loads(data)
                                        await message_queue.put(message)
                                        print("Received:", message)
                                    except json.JSONDecodeError:
                                        print("Received data (not JSON):", data)

                                elif decoded_line:  # Log any other lines
                                     print(f"Received (non-data):", decoded_line)

                            except UnicodeDecodeError:
                                print("Received non-text data.")


                else:
                    print(f"Error: SSE connection failed with status {response.status}")
                    return None, None  # Return None, None on failure

    except aiohttp.ClientError as e:
        print(f"Error connecting to SSE endpoint: {e}")
        return None, None  # Return None, None on connection errors
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, None

    return messages_url, session_id



async def post_message(url: str, message: dict):
    """Posts a message to the /messages endpoint."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=message) as response:
                if response.status == 202:
                    print("Message posted successfully.")
                    return True  # Indicate success
                elif response.status in (400, 404, 500):  # More specific error handling
                    print(f"Server returned error: {response.status} - {await response.text()}")
                    return False
                else:
                    print(f"Failed to post message: {response.status} - {await response.text()}")
                    return False
        except aiohttp.ClientError as e:
            print(f"Client error posting message: {e}")  # More specific error
            return False
        except Exception as e:
            print(f"An unexpected error occurred while posting: {e}")
            return False


async def main():
    sse_url = "http://0.0.0.0:8080/sse"
    message_queue = asyncio.Queue()

    messages_url, session_id = await sse_client(sse_url, message_queue)

    if not messages_url or not session_id:
        print("Failed to retrieve messages endpoint or session ID. Exiting.")
        return

    print(f"Connecting to messages url {messages_url} with session ID {session_id}")

    # Example 1: Get weather forecast
    latitude = 34.0522  # Example: Los Angeles
    longitude = -118.2437
    message_forecast = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "session_id": session_id,  # Include the session_id
            "tool_name": "get_forecast",
            "arguments": {"latitude": latitude, "longitude": longitude},
        },
    }
    forecast_posted = await post_message(messages_url, message_forecast)
    if not forecast_posted:
        print("Failed to post forecast request.")
    else:
        print("Successfully requested forecast.")

    # Example 2: Get weather alerts
    await asyncio.sleep(5)
    state = "CA"
    message_alerts = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "session_id": session_id,  # Include the session_id
            "tool_name": "get_alerts",
            "arguments": {"state": state},
        },
    }
    alerts_posted = await post_message(messages_url, message_alerts)
    if not alerts_posted:
        print("Failed to post alerts request.")
    else:
        print("Successfully requested alerts.")

    await asyncio.sleep(5) # Let it work


if __name__ == "__main__":
    import asyncio
    import aiohttp
    import json
    import urllib.parse
    import uuid
    asyncio.run(main())