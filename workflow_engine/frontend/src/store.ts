import { create } from 'zustand';

export interface Node {
  id: string;
  type: string;
  position: { x: number; y: number };
}

export interface Connection {
  source: string;
  target: string;
}

export interface WorkflowState {
  nodes: Node[];
  connections: Connection[];
  addNode: (node: Node) => void;
  updateNodePosition: (nodeId: string, position: { x: number; y: number }) => void;
}

export const useWorkflowStore = create<WorkflowState>((set) => ({
  nodes: [
    // Add some initial nodes for demonstration
    { id: '1', type: 'InputNode', position: { x: 100, y: 100 } },
    { id: '2', type: 'LLMNode', position: { x: 400, y: 100 } },
  ],
  connections: [
    { source: '1', target: '2' },
  ],
  addNode: (node) =>
    set((state) => ({
      nodes: [...state.nodes, node],
    })),
  updateNodePosition: (nodeId, position) =>
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId ? { ...node, position } : node
      ),
    })),
}));
