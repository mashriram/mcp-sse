import asyncio
import os
from typing import Optional, List, Any
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client
import streamlit as st
from dotenv import load_dotenv

# Langchain imports
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool

# Load environment variables from .env file
load_dotenv()


class ToolWrapper(BaseTool):
    """A wrapper to make MCP tools compatible with Langchain."""
    name: str
    description: str
    input_schema: dict
    session: ClientSession

    async def _run(self, **kwargs: Any) -> str:
        """Execute the tool."""
        try:
            result = await self.session.call_tool(self.name, kwargs)
            return result.content[0].text
        except Exception as e:
            return f"Error calling tool {self.name}: {e}"


class MCPClient:
    """A client to connect to a single MCP server."""

    def __init__(self, api_key: str, server_url: str):
        self.server_url = server_url
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        if not api_key:
            raise ValueError("Groq API key not provided.")
        self.llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=api_key)
        self._streams_context = None
        self._session_context = None
        self.tools = []

    async def connect(self):
        """Connect to the MCP server and list its tools."""
        self._streams_context = sse_client(url=self.server_url)
        streams = await self._streams_context.__aenter__()
        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()
        await self.session.initialize()
        response = await self.session.list_tools()
        self.tools = response.tools
        return [tool.name for tool in self.tools]

    async def cleanup(self):
        """Disconnect from the MCP server."""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)
        self.session = None
        self.tools = []


async def process_query_with_clients(
    messages: List[BaseMessage], clients: List[MCPClient], llm: ChatGroq
) -> str:
    """Process a query using tools from multiple MCP clients."""
    all_tools = []
    for client in clients:
        for tool in client.tools:
            all_tools.append(
                ToolWrapper(
                    name=tool.name,
                    description=tool.description,
                    input_schema=tool.inputSchema,
                    session=client.session,
                )
            )

    llm_with_tools = llm.bind_tools(all_tools)

    response_parts = []
    max_iterations = 5
    for _ in range(max_iterations):
        llm_response: BaseMessage = await llm_with_tools.ainvoke(messages)
        if not isinstance(llm_response, AIMessage):
            response_parts.append(f"[Error: Unexpected response type {type(llm_response)}]")
            break

        messages.append(llm_response)
        ai_content = llm_response.content
        if isinstance(ai_content, str) and ai_content.strip():
            response_parts.append(ai_content)

        if not llm_response.tool_calls:
            break

        response_parts.append(f"[Processing {len(llm_response.tool_calls)} tool call(s)]")
        for tool_call in llm_response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            response_parts.append(f"[Calling tool '{tool_name}' with args: {tool_args}]")

            tool_message_content = ""
            try:
                tool_to_call = next((t for t in all_tools if t.name == tool_name), None)
                if tool_to_call:
                    tool_result_str = await tool_to_call.arun(**tool_args)
                    tool_message_content = tool_result_str
                    response_parts.append(f"[Tool '{tool_name}' Result: {tool_message_content}]")
                else:
                    tool_message_content = f"Error: Tool '{tool_name}' not found."
                    response_parts.append(f"[{tool_message_content}]")
            except Exception as e:
                tool_message_content = f"Error executing tool '{tool_name}': {e}"
                response_parts.append(f"[{tool_message_content}]")

            messages.append(ToolMessage(content=tool_message_content, tool_call_id=tool_call_id))
    else:
        response_parts.append("[Processing finished due to maximum iterations]")

    final_response = "\n".join(part for part in response_parts if not part.startswith("["))
    if messages and isinstance(messages[-1], ToolMessage):
        final_llm_response = await llm_with_tools.ainvoke(messages)
        if isinstance(final_llm_response, AIMessage) and final_llm_response.content:
            final_response += "\n\n" + str(final_llm_response.content)

    return final_response.strip()


# --- Streamlit App ---

st.title("MCP Chat Client")

# --- Sidebar ---

st.sidebar.title("Configuration")
if "api_key" not in st.session_state:
    st.session_state.api_key = os.environ.get("GROQ_API_KEY", "")

api_key = st.sidebar.text_input("Groq API Key", type="password", value=st.session_state.api_key)
if api_key:
    st.session_state.api_key = api_key

st.sidebar.title("MCP Servers")
AVAILABLE_SERVERS = {
    "Weather Server": "http://localhost:8080/sse",
    "Time Server (Demo)": "http://localhost:8081/sse",
}

selected_server_urls = [
    url for name, url in AVAILABLE_SERVERS.items() if st.sidebar.checkbox(f"Use {name}", value=True)
]

st.sidebar.subheader("Status")
connection_status = st.sidebar.empty()

if "mcp_clients" not in st.session_state:
    st.session_state.mcp_clients = []

if st.sidebar.button("Connect"):
    if api_key:
        if selected_server_urls:
            clients = []
            try:
                for url in selected_server_urls:
                    client = MCPClient(api_key=api_key, server_url=url)
                    asyncio.run(client.connect())
                    clients.append(client)
                st.session_state.mcp_clients = clients
            except Exception as e:
                connection_status.error(f"Connection failed: {e}")
        else:
            connection_status.warning("No servers selected.")
    else:
        connection_status.error("Please enter your Groq API key.")

if st.sidebar.button("Disconnect"):
    if st.session_state.mcp_clients:
        for client in st.session_state.mcp_clients:
            asyncio.run(client.cleanup())
        st.session_state.mcp_clients = []

if st.session_state.mcp_clients:
    all_tools = [tool.name for client in st.session_state.mcp_clients for tool in client.tools]
    connection_status.success(f"Connected! Tools: {all_tools}")
else:
    connection_status.info("Not connected.")

# --- Chat Interface ---

st.header("Chat")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What can you do?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if st.session_state.mcp_clients:
        with st.spinner("Thinking..."):
            history = [
                (
                    HumanMessage(content=m["content"])
                    if m["role"] == "user"
                    else AIMessage(content=m["content"])
                )
                for m in st.session_state.messages
            ]
            llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=st.session_state.api_key)
            response = asyncio.run(
                process_query_with_clients(history, st.session_state.mcp_clients, llm)
            )
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
    else:
        st.warning("Please connect to an MCP server first.")
