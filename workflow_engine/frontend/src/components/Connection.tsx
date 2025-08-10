import { Node } from "@/store";

interface ConnectionProps {
  sourceNode: Node;
  targetNode: Node;
}

export function Connection({ sourceNode, targetNode }: ConnectionProps) {
  // For simplicity, we'll connect the center of the nodes.
  // A more advanced implementation would connect to specific handles on the node.
  const sourceX = sourceNode.position.x + 128; // Half of card width (w-64)
  const sourceY = sourceNode.position.y + 36;  // Half of card header height
  const targetX = targetNode.position.x + 128;
  const targetY = targetNode.position.y + 36;

  const pathData = `M ${sourceX} ${sourceY} L ${targetX} ${targetY}`;

  return (
    <svg className="absolute top-0 left-0 w-full h-full pointer-events-none">
      <path
        d={pathData}
        stroke="gray"
        strokeWidth="2"
        fill="none"
      />
    </svg>
  );
}
