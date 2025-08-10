from collections import deque
from typing import List, Dict, Any
from .models import Workflow, Node as WorkflowNode
from .nodes import create_node_instance

class WorkflowExecutionError(Exception):
    """Custom exception for workflow execution errors."""
    pass

class WorkflowExecutor:
    """
    Executes a workflow defined by a Workflow object.
    """

    def __init__(self, workflow: Workflow):
        self.workflow = workflow
        self.node_map = {node.id: node for node in workflow.nodes}
        self.adj = {node.id: [] for node in self.workflow.nodes}
        self.reverse_adj = {node.id: [] for node in self.workflow.nodes}

        for conn in self.workflow.connections:
            self.adj[conn.source].append(conn.target)
            self.reverse_adj[conn.target].append(conn.source)

    def _topological_sort(self) -> List[WorkflowNode]:
        """
        Performs a topological sort of the workflow nodes.
        """
        in_degree = {node.id: 0 for node in self.workflow.nodes}
        for node_id in self.adj:
            for neighbor_id in self.adj[node_id]:
                in_degree[neighbor_id] += 1

        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        sorted_order = []

        while queue:
            u_id = queue.popleft()
            sorted_order.append(self.node_map[u_id])

            for v_id in self.adj[u_id]:
                in_degree[v_id] -= 1
                if in_degree[v_id] == 0:
                    queue.append(v_id)

        if len(sorted_order) != len(self.workflow.nodes):
            raise WorkflowExecutionError("Workflow contains a cycle and cannot be executed.")

        return sorted_order

    async def execute(self, initial_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes the workflow asynchronously.

        Args:
            initial_data: A dictionary where keys are InputNode IDs and values are their data.

        Returns:
            A dictionary containing the final output of the workflow.
        """
        sorted_nodes = self._topological_sort()
        node_outputs: Dict[str, Any] = {}

        print("Execution Order:", [node.id for node in sorted_nodes])

        for node_model in sorted_nodes:
            try:
                node_instance = create_node_instance(node_model.type, node_model.config)
            except ValueError as e:
                print(f"Skipping node {node_model.id} ({node_model.type}): {e}")
                node_outputs[node_model.id] = f"Error: Unknown node type '{node_model.type}'"
                continue

            predecessor_ids = self.reverse_adj.get(node_model.id, [])
            inputs = [node_outputs[pid] for pid in predecessor_ids]

            if node_model.type == "InputNode":
                if initial_data and node_model.id in initial_data:
                    node_instance.config = initial_data[node_model.id]

            print(f"\nExecuting node {node_model.id} ({node_model.type})")
            output = await node_instance.execute(inputs)
            node_outputs[node_model.id] = output
            print(f"Output of {node_model.id}: {output}")

        final_outputs = {
            node.id: node_outputs.get(node.id)
            for node in self.workflow.nodes
            if node.type == "OutputNode"
        }

        return final_outputs
