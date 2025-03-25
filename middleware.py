# middleware.py

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
import uvicorn
import argparse
import subprocess
import sys
import asyncio
import os
import json
from mcp.types import JSONRPCMessage
import urllib.parse
import uuid
from typing import AsyncGenerator


async def run_mcp_tool(server_path: str, tool_name: str, tool_args: dict) -> str:
    """
    Runs a single MCP tool in the server process and captures its output.
    """
    try:
        # Construct the input for the server.
        input_data = json.dumps({"tool_name": tool_name, "arguments": tool_args})
        print(f"Sending to weather_stdio: {input_data}", file=sys.stderr)  # Log to stderr

        process = await asyncio.create_subprocess_exec(
            sys.executable,
            server_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Send the input and close stdin
        stdout, stderr = await process.communicate(input=input_data.encode())
        print(f"weather_stdio process completed with returncode: {process.returncode}", file=sys.stderr)

        if process.returncode != 0:
            error_message = (
                f"MCP server exited with code {process.returncode}\n{stderr.decode()}"
            )
            print(error_message, file=sys.stderr)  # Log to stderr
            return error_message
        else:
            output = stdout.decode().strip()
            print(f"weather_stdio returned: {output}", file=sys.stderr) # Log to stderr
            return output

    except FileNotFoundError:
        error_message = f"Error: Server file not found at {server_path}"
        print(error_message, file=sys.stderr) # Log to stderr
        return error_message
    except Exception as e:
        error_message = f"Error running MCP server: {e}"
        print(error_message, file=sys.stderr)  # Log to stderr
        return error_message


def create_starlette_app(server_path: str, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the MCP server with SSE."""

    async def handle_sse(request: Request) -> StreamingResponse:
        """Handles SSE connection requests."""

        # Generate a session ID
        session_id = str(uuid.uuid4())
        messages_url = f"/messages/?session_id={session_id}"
        print(f"New SSE connection. Session ID: {session_id}", file=sys.stderr)

        async def event_stream() -> AsyncGenerator[bytes, None]:
            # Send initial endpoint message.
            yield (
                f"event: endpoint\ndata: {json.dumps({'messages_url': messages_url})}\n\n"
            ).encode("utf-8")

            # Keep the connection alive (but don't expect *incoming* messages on SSE).
            while True:
                try:
                    await asyncio.sleep(60)  # Keep the connection alive
                except asyncio.CancelledError:
                    print("SSE connection closing", file=sys.stderr)
                    break
                except Exception as e:
                    print(f"Error in event_stream: {e}", file=sys.stderr)
                    break

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    async def handle_messages(request: Request):
        """Handles POST requests to the /messages/ endpoint."""
        try:
            data = await request.json()
            print(f"Received message: {data}", file=sys.stderr) # Log to stderr

            session_id = data.get("session_id")
            tool_name = data.get("tool_name")
            tool_args = data.get("arguments", {})

            if not session_id or not tool_name:
                error_message = "Invalid request: Missing session_id or tool_name"
                print(error_message, file=sys.stderr)
                return JSONResponse({"error": error_message}, status_code=400)

            tool_args["session_id"] = session_id # Add session ID

            result = await run_mcp_tool(server_path, tool_name, tool_args)
            print(f"Returning result: {result}", file=sys.stderr)
            return JSONResponse({"result": result}, status_code=200)

        except json.JSONDecodeError:
            error_message = "Invalid JSON"
            print(error_message, file=sys.stderr)  # Log to stderr
            return JSONResponse({"error": error_message}, status_code=400)
        except Exception as e:
            error_message = f"Error processing message: {e}"
            print(error_message, file=sys.stderr)  # Log to stderr
            return JSONResponse({"error": error_message}, status_code=500)

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
        ],
    )

async def main(server_path: str, host: str, port: int):
    """Main function to run the middleware and MCP server."""
    if not os.path.exists(server_path):
        print(f"Error: Server file not found at {server_path}")
        return

    starlette_app = create_starlette_app(server_path, debug=True)

    config = uvicorn.Config(starlette_app, host=host, port=port)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MCP SSE-based middleware")
    parser.add_argument("server_path", help="Path to the MCP server Python file")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    args = parser.parse_args()

    asyncio.run(main(args.server_path, args.host, args.port))