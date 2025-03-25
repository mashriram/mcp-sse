import asyncio
from typing import Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dotenv import load_dotenv
import json
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
import re  # Import the regular expression module
import codecs

load_dotenv()


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.groq = ChatGroq(temperature=0.0)

        # Define a system message to guide Groq on tool use
        self.system_message = SystemMessage(
            content="""You are a helpful AI assistant that can use tools to get information.
            You have access to the following tools:
            - get_alerts: Get weather alerts for a US state.  Arguments: {"state": "US state code"}
            - get_forecast: Get weather forecast for a location. Arguments: {"latitude": "latitude", "longitude": "longitude"}

            When you want to use a tool, include a JSON object in your response like this:
            {"tool_name": "tool_name", "arguments": {"arg1": "value1", "arg2": "value2"}}

            Otherwise, respond with a normal text response.
            """
        )

    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command, args=[server_script_path], env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Groq and available tools"""
        messages = [self.system_message, HumanMessage(content=query)]

        response = await self.session.list_tools()
        available_tools = {tool.name: tool.description for tool in response.tools}

        print(f"available tools: {available_tools}")
        print(f"messages: {messages}")

        # Invoke Groq
        groq_response = self.groq.invoke(messages)
        response_text = groq_response.content

        print(f"Groq Response: {response_text}")

        # Simplified extraction: Find first '{' and last '}'
        start_index = response_text.find("{")
        end_index = response_text.rfind("}")

        if start_index != -1 and end_index != -1 and start_index < end_index:
            json_string = response_text[start_index : end_index + 1]
            print(f"Extracted JSON: {json_string}")

            # Targeted cleaning
            json_string = json_string.replace(
                r"\/", "/"
            )  # Remove escaped forward slashes
            json_string = json_string.replace(r"\_", "_")  # Remove escaped underscores
            try:
                json_string = codecs.decode(
                    json_string, "unicode_escape"
                )  # Decode unicode escapes
            except:
                pass  # if it fails do nothing

            try:
                tool_call = json.loads(json_string)
                tool_name = tool_call.get("tool_name")
                tool_args = tool_call.get("arguments", {})

                if tool_name and tool_name in available_tools:
                    print(f"Groq wants to use tool: {tool_name} with args: {tool_args}")

                    # Execute tool call
                    result = await self.session.call_tool(tool_name, tool_args)
                    print(f"Tool Result: {result}")

                    # Extract text content from result
                    if hasattr(result, "content") and isinstance(result.content, list):
                        tool_result_text = " ".join(
                            [
                                item.text
                                for item in result.content
                                if hasattr(item, "text")
                            ]
                        )
                    else:
                        tool_result_text = str(
                            result.content
                        )  # Fallback to string conversion

                    # Get the next response from Groq, feeding it the tool result
                    groq_response = self.groq.invoke(
                        [HumanMessage(content=tool_result_text)]
                    )
                    final_text = groq_response.content

                else:
                    final_text = "Invalid tool name or format. Please use the correct tool format."

            except (json.JSONDecodeError, ValueError, TypeError) as e:
                final_text = f"Error parsing or using tool call: {e}"

        else:
            final_text = response_text  # If no tool is used, then it would just give the response

        return final_text

    async def chat_loop(self):
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())