import { useDraggable } from "@dnd-kit/core";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Node as NodeType } from "@/store";

interface NodeProps {
  node: NodeType;
}

export function Node({ node }: NodeProps) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: node.id,
  });

  const style = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
      }
    : {};

  return (
    <div
      ref={setNodeRef}
      style={{
        position: "absolute",
        left: node.position.x,
        top: node.position.y,
        ...style,
      }}
      {...listeners}
      {...attributes}
    >
      <Card className="w-64 cursor-grab">
        <CardHeader>
          <CardTitle>{node.type}</CardTitle>
        </CardHeader>
      </Card>
    </div>
  );
}
