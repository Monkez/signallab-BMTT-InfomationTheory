import type { MiniMapNodeProps } from '@xyflow/react'

export function FlowMiniMapNode({ x, y, width, height, color, strokeColor, strokeWidth, borderRadius, shapeRendering, selected }: MiniMapNodeProps) {
  return <g>
    <rect x={x} y={y} width={width} height={height} rx={borderRadius} fill={color} stroke={selected ? '#1f57ba' : strokeColor} strokeWidth={selected ? 2 : strokeWidth} shapeRendering={shapeRendering} />
    {width > 10 && <rect x={x + 2} y={y + 2} width={Math.min(4, width / 3)} height={Math.max(3, height - 4)} rx={1.5} fill="#fff" opacity={0.65} />}
  </g>
}
