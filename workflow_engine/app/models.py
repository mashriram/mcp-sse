from pydantic import BaseModel
from typing import List, Dict, Any

class Node(BaseModel):
    """Represents a single node in the workflow."""
    id: str
    type: str
    config: Dict[str, Any] = {}

class Connection(BaseModel):
    """Represents a connection between two nodes in the workflow."""
    source: str  # The ID of the source node
    target: str  # The ID of the target node

class Workflow(BaseModel):
    """Represents a complete workflow with all its nodes and connections."""
    id: str
    name: str
    nodes: List[Node]
    connections: List[Connection]
