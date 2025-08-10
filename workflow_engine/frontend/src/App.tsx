import { DndContext, DragEndEvent } from "@dnd-kit/core";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Node } from "@/components/Node";
import { Connection } from "@/components/Connection";
import { useWorkflowStore } from "@/store";

function App() {
  const { nodes, connections, updateNodePosition } = useWorkflowStore((state) => ({
    nodes: state.nodes,
    connections: state.connections,
    updateNodePosition: state.updateNodePosition,
  }));

  const nodeMap = new Map(nodes.map((node) => [node.id, node]));

  function handleDragEnd(event: DragEndEvent) {
    const { active, delta } = event;
    const nodeId = active.id as string;
    const node = nodeMap.get(nodeId);

    if (node) {
      const newPosition = {
        x: node.position.x + delta.x,
        y: node.position.y + delta.y,
      };
      updateNodePosition(nodeId, newPosition);
    }
  }

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="flex h-screen bg-background text-foreground">
        {/* Left Sidebar */}
        <aside className="w-72 border-r p-4">
          <h2 className="text-xl font-bold mb-4">Nodes</h2>
          <div className="space-y-2">
            <Card className="p-4 cursor-pointer hover:bg-accent">
              <CardTitle className="text-base">Input Node</CardTitle>
            </Card>
            <Card className="p-4 cursor-pointer hover:bg-accent">
              <CardTitle className="text-base">LLM Node</CardTitle>
            </Card>
            <Card className="p-4 cursor-pointer hover:bg-accent">
              <CardTitle className="text-base">MCP Node</CardTitle>
            </Card>
            <Card className="p-4 cursor-pointer hover:bg-accent">
              <CardTitle className="text-base">Output Node</CardTitle>
            </Card>
          </div>
        </aside>

        {/* Main Canvas */}
        <main className="flex-1 relative">
          {nodes.map((node) => (
            <Node key={node.id} node={node} />
          ))}
          {connections.map((conn) => {
            const sourceNode = nodeMap.get(conn.source);
            const targetNode = nodeMap.get(conn.target);
            if (!sourceNode || !targetNode) {
              return null;
            }
            return (
              <Connection
                key={`${conn.source}-${conn.target}`}
                sourceNode={sourceNode}
                targetNode={targetNode}
              />
            );
          })}
        </main>

        {/* Right Properties Panel */}
        <aside className="w-80 border-l p-4">
          <h2 className="text-xl font-bold mb-4">Properties</h2>
          <div className="text-center text-muted-foreground pt-10">
            <p>Select a node to see its properties.</p>
          </div>
        </aside>
      </div>
    </DndContext>
  );
}

export default App;
