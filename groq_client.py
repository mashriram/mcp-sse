import asyncio
import json
import os
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # self.anthropic = Anthropic()
        self.groq = ChatGroq(temperature=0.0)

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport"""
        # Store the context managers so they stay alive
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        # Initialize
        await self.session.initialize()

        # List available tools to verify connection
        print("Initialized SSE client...")
        print("Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        print(f"toolsList: {response}")
        available_tools = [{ 
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        llm_with_tools = self.groq.bind_tools(available_tools)
        response = llm_with_tools.invoke(messages)
        print(f"response_from_llm: {response}")
        print(f"tool_calls: {response.tool_calls}")
        # Initial Claude API call
        # response = self.anthropic.messages.create(
        #     model="claude-3-5-sonnet-20241022",
        #     max_tokens=1000,
        #     messages=messages,
        #     tools=available_tools
        # )
        
        # Process response and handle tool calls
        tool_results = []
        final_text = []

        # for content in response.content:
        content = response.content
        
        if response.tool_calls is not None and len(response.tool_calls) > 0 and response.tool_calls[0]['type'] == "tool_call":
            tool_name = response.tool_calls[0]['name']
            tool_args = response.tool_calls[0]['args']
            print(f"tool_name: {tool_name}")
            print(f"tool_args: {tool_args}")
            
            # Execute tool call
            print("about to execute the tool")
            result = await self.session.call_tool(tool_name, tool_args)
            print(f"tool_call_result: {result}")
            
            tool_results.append({"call": tool_name, "result": result})
            final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
            print(f"tool_results: {tool_results}")
            print(f"final_text: {final_text}")
            print(f"result_content:{result.content}")

            # Continue conversation with tool results
            if hasattr(result.content, 'text') and result.content.text:
                messages.append({
                "role": "assistant",
                "content": result.content.text
                })
            messages.append({
                "role": "user", 
                "content": query
            })

            # Get next response from Claude
            # response = self.anthropic.messages.create(
            #     model="claude-3-5-sonnet-20241022",
            #     max_tokens=1000,
            #     messages=messages,
            # )
            print(f"about to call llm: {messages}")
            response = self.groq.invoke(messages)
            print(response)

            final_text.append(response.content)
            
        elif type(content) is str:
            final_text.append(content)

        return final_text
    

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print(response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")


async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run client.py <URL of SSE MCP server (i.e. http://localhost:8080/sse)>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_sse_server(server_url=sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys
    asyncio.run(main())
