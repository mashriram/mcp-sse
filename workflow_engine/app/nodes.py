from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseNode(ABC):
    """Abstract base class for all nodes in the workflow."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def execute(self, inputs: List[Any]) -> Any:
        """
        Executes the node's logic asynchronously.

        Args:
            inputs: A list of outputs from the node's predecessors.

        Returns:
            The output of the node.
        """
        pass

class InputNode(BaseNode):
    """A node that provides the initial input to the workflow."""

    async def execute(self, inputs: List[Any]) -> Any:
        print("Executing InputNode")
        return self.config

class OutputNode(BaseNode):
    """A node that represents the end of a workflow branch."""

    async def execute(self, inputs: List[Any]) -> Any:
        print(f"Executing OutputNode with input: {inputs}")
        return inputs[0] if inputs else None

class LLMNode(BaseNode):
    """A node that simulates a call to a Large Language Model."""

    async def execute(self, inputs: List[Any]) -> Any:
        model_name = self.config.get("model_name", "default_model")
        prompt = inputs[0] if inputs else ""

        print(f"Executing LLMNode (model: {model_name}) with prompt: '{prompt}'")

        # In a real implementation, this would be an async API call.
        response = f"This is a simulated response from {model_name} for the prompt: '{prompt}'"
        return response

from mcp import ClientSession
from mcp.client.sse import sse_client
from contextlib import AsyncExitStack

class MCPNode(BaseNode):
    """A node that connects to an MCP server and executes a tool."""

    async def execute(self, inputs: List[Any]) -> Any:
        server_url = self.config.get("server_url")
        tool_name = self.config.get("tool_name")

        if not server_url or not tool_name:
            raise ValueError("MCPNode config must include 'server_url' and 'tool_name'")

        # The input to this node is expected to be a dictionary of arguments for the tool.
        tool_args = inputs[0] if inputs else {}
        if not isinstance(tool_args, dict):
            raise TypeError(f"MCPNode input must be a dictionary of tool arguments, but got {type(tool_args)}")

        print(f"Executing MCPNode: calling tool '{tool_name}' on server '{server_url}' with args {tool_args}")

        async with AsyncExitStack() as stack:
            streams_context = sse_client(url=server_url)
            streams = await stack.enter_async_context(streams_context)

            session_context = ClientSession(*streams)
            session: ClientSession = await stack.enter_async_context(session_context)

            await session.initialize()

            # Here we could list tools to verify the tool_name exists, but for now we'll just call it.
            # response = await session.list_tools()

            result = await session.call_tool(tool_name, tool_args)

            # Assuming the result has content with a text part
            if result.content and result.content[0].text:
                return result.content[0].text
            else:
                return "Tool executed, but returned no content."


# A factory to create node instances from their type name.
NODE_CLASS_MAP = {
    "InputNode": InputNode,
    "OutputNode": OutputNode,
    "LLMNode": LLMNode,
    "MCPNode": MCPNode,
}

def create_node_instance(node_type: str, config: Dict[str, Any]) -> BaseNode:
    """Creates an instance of a node class based on its type."""
    node_class = NODE_CLASS_MAP.get(node_type)
    if not node_class:
        raise ValueError(f"Unknown node type: {node_type}")
    return node_class(config)
