import asyncio
import json
import os
from typing import Optional, List, Dict, Any
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client

from dotenv import load_dotenv

# Langchain imports
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import chain
from langchain_core.tools import BaseTool,Tool

load_dotenv()  # load environment variables from .env



# Define a Tool class compatible with Langchain
class ToolWrapper(BaseTool):
    name: str
    description: str
    input_schema: dict  # Schema of the input parameters
    session: ClientSession  # MCP Client Session

    async def _run(self, **kwargs: Any) -> str:
        """Use the tool."""
        try:
            result = await self.session.call_tool(self.name, kwargs)
            print(result)
            return result.content[0].text
        except Exception as e:
            return f"Error calling tool {self.name}: {e}"

    async def arun(self, **kwargs: Any) -> str:
        """Use the tool asynchronously."""
        return await self._run(**kwargs)

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.groq_api_key = os.environ.get("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")
        self.llm = ChatGroq(model="llama-3.1-8b-instant",groq_api_key=self.groq_api_key) # Initialize ChatGroq with API key
        self._streams_context = None
        self._session_context = None

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
        """Process a query using Langchain and Groq LLM with available tools"""
        # (Tool loading remains the same - using ToolWrapper)
        response = await self.session.list_tools()
        available_tools_raw = response.tools
        available_tools: List[BaseTool] = [
            ToolWrapper(
                name=tool.name,
                description=tool.description,
                input_schema=tool.inputSchema,
                session=self.session
            )
            for tool in available_tools_raw
        ]
        print("Langchain Tools initialized:", [t.name for t in available_tools])

        messages: List[BaseMessage] = [HumanMessage(content=query)]
        # Use a list to collect parts of the final response, including potential intermediate steps
        response_parts = []

        llm_with_tools = self.llm.bind_tools(available_tools)

        max_iterations = 5 # Reduced max iterations to prevent runaway loops during debugging
        for i in range(max_iterations):
            print(f"\n--- Iteration {i+1} ---")
            print("Current Messages:", messages)
            try:
                 llm_response: BaseMessage = await llm_with_tools.ainvoke(messages)
                 print("LLM Response:", llm_response)
            except Exception as e:
                 # Handle API errors during invoke
                 error_msg = f"Error invoking LLM: {e}"
                 print(error_msg)
                 # Check if it's the specific Groq tool use error
                 if "tool_use_failed" in str(e):
                      error_msg += "\nGroq reported an issue processing tool calls/results. This might be due to incorrect arguments or unexpected tool output format in the history."
                 response_parts.append(f"[LLM Invocation Error: {error_msg}]")
                 break # Stop processing on LLM error


            if not isinstance(llm_response, AIMessage):
                 print(f"Unexpected LLM response type: {type(llm_response)}. Stopping.")
                 response_parts.append(f"[Error: Unexpected response type {type(llm_response)}]")
                 break

            # Add the AI response (potentially containing tool calls) to history
            messages.append(llm_response)

            # Capture content from the AI message if any
            ai_content = llm_response.content
            if isinstance(ai_content, str) and ai_content.strip():
                print(f"LLM Content: {ai_content}")
                # Don't add it to final response *yet* if tool calls are happening,
                # wait for the final summarization. Add intermediate thoughts if needed.
                # response_parts.append(ai_content) # Optionally add intermediate thoughts

            # Check for tool calls
            if not llm_response.tool_calls:
                print("LLM finished without tool calls.")
                # If there are no tool calls, this should be the final answer.
                if isinstance(ai_content, str) and ai_content.strip():
                     response_parts.append(ai_content) # Add final answer
                else:
                     # Handle cases where LLM stops without content after tool use
                     response_parts.append("[LLM finished processing but provided no final content.]")
                break # Exit loop

            # --- Process Tool Calls ---
            response_parts.append(f"[Processing {len(llm_response.tool_calls)} tool call(s)]")
            for tool_call in llm_response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                tool_call_id = tool_call['id']

                print(f"Attempting to call tool: {tool_name} with args: {tool_args}")
                response_parts.append(f"[Calling tool '{tool_name}' with args: {tool_args}]")

                tool_message_content = ""
                try:
                    tool_to_call = next((t for t in available_tools if t.name == tool_name), None)
                    if tool_to_call:
                        # Use the corrected ToolWrapper which returns a string
                        tool_result_str = await tool_to_call.arun(**tool_args)
                        tool_message_content = tool_result_str # Already a string now
                        print(f"Tool '{tool_name}' result: {tool_message_content}")
                        response_parts.append(f"[Tool '{tool_name}' Result: {tool_message_content}]")
                    else:
                        tool_message_content = f"Error: Tool '{tool_name}' not found."
                        print(tool_message_content)
                        response_parts.append(f"[{tool_message_content}]")

                except Exception as e:
                    tool_message_content = f"Error executing tool '{tool_name}' with args {tool_args}: {e}"
                    print(tool_message_content)
                    import traceback
                    traceback.print_exc()
                    response_parts.append(f"[{tool_message_content}]")

                # Add the ToolMessage with the string result to history
                messages.append(ToolMessage(content=tool_message_content, tool_call_id=tool_call_id))
            # --- End Tool Call Processing ---
            # Loop continues, LLM will process the ToolMessage results

        else:
             # If loop finishes due to max_iterations
             print("Reached maximum iterations.")
             response_parts.append("[Processing finished due to maximum iterations]")

        # Join the collected parts for the final output string
        # Filter out potentially noisy intermediate messages if desired, or keep for debug
        # final_response = "\n".join([part for part in response_parts if not part.startswith("[Calling tool") and not part.startswith("[Tool ")])
        final_response = "\n".join(response_parts) # Keep all parts for now for debugging
        # Try to get one last response from the LLM to summarize if the last message was a ToolMessage
        if messages and isinstance(messages[-1], ToolMessage):
             print("\n--- Final Summarization Step ---")
             try:
                 final_llm_response = await llm_with_tools.ainvoke(messages)
                 if isinstance(final_llm_response, AIMessage) and final_llm_response.content:
                      print("Final LLM Summary:", final_llm_response.content)
                      final_response += "\n\n" + str(final_llm_response.content) # Append final summary
             except Exception as e:
                  print(f"Error during final summarization: {e}")
                  final_response += "\n[Error during final summarization]"


        return final_response.strip() # Return the assembled response

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
                print("\n" + response)

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