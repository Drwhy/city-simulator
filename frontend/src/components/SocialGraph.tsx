import { useEffect, useMemo, useState } from "react";
import { getSocialGraph } from "../api";
import type { SocialGraphData } from "../types/city";

type GraphFilter = "significant" | "all" | "conflicts";

interface SocialGraphProps {
  open: boolean;
  onClose: () => void;
  onSelectCitizen: (citizenId: number) => void;
  selectedCitizenId?: number | null;
  paused: boolean;
  snapshotTick: number;
}

const WIDTH = 1180;
const HEIGHT = 720;

function edgeVisible(edge: SocialGraphData["edges"][number], filter: GraphFilter): boolean {
  if (filter === "all") return true;
  if (filter === "conflicts") return edge.status === "rival" || edge.conflictLevel > 0;
  return ["friend", "close_friend", "rival"].includes(edge.status) || edge.conflictLevel >= 2;
}

function edgeClass(edge: SocialGraphData["edges"][number]): string {
  if (edge.conflictLevel >= 3) return "graph-edge graph-edge-severe";
  if (edge.status === "rival" || edge.conflictLevel > 0) return "graph-edge graph-edge-rival";
  if (edge.status === "close_friend") return "graph-edge graph-edge-close";
  if (edge.status === "friend") return "graph-edge graph-edge-friend";
  return "graph-edge graph-edge-known";
}

export function SocialGraph({ open, onClose, onSelectCitizen, selectedCitizenId = null, paused, snapshotTick }: SocialGraphProps) {
  const [data, setData] = useState<SocialGraphData | null>(null);
  const [filter, setFilter] = useState<GraphFilter>("significant");
  const [hoveredNode, setHoveredNode] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    let disposed = false;
    const refresh = async (initial: boolean) => {
      if (initial) setLoading(true);
      try {
        const graph = await getSocialGraph();
        if (!disposed) setData(graph);
      } finally {
        if (!disposed) setLoading(false);
      }
    };
    void refresh(data === null);
    const timer = paused ? null : window.setInterval(() => void refresh(false), 5000);
    return () => {
      disposed = true;
      if (timer !== null) window.clearInterval(timer);
    };
  }, [open, paused, paused ? snapshotTick : 0]);

  const positions = useMemo(() => {
    if (!data) return new Map<number, { x: number; y: number }>();
    const groups = new Map<number, typeof data.nodes>();
    data.nodes.forEach((node) => {
      const key = node.householdId ?? -node.id;
      const group = groups.get(key) ?? [];
      group.push(node);
      groups.set(key, group);
    });
    const orderedGroups = [...groups.entries()].sort((a, b) => a[0] - b[0]);
    const result = new Map<number, { x: number; y: number }>();
    orderedGroups.forEach(([, nodes], groupIndex) => {
      const angle = (groupIndex / Math.max(1, orderedGroups.length)) * Math.PI * 2 - Math.PI / 2;
      const ring = groupIndex % 3;
      const centerX = WIDTH / 2 + Math.cos(angle) * (250 + ring * 70);
      const centerY = HEIGHT / 2 + Math.sin(angle) * (220 + ring * 42);
      nodes.forEach((node, index) => {
        const localAngle = (index / Math.max(1, nodes.length)) * Math.PI * 2;
        const radius = nodes.length === 1 ? 0 : 14 + nodes.length * 2.1;
        result.set(node.id, {
          x: centerX + Math.cos(localAngle) * radius,
          y: centerY + Math.sin(localAngle) * radius,
        });
      });
    });
    return result;
  }, [data]);

  const visibleEdges = useMemo(
    () => data?.edges.filter((edge) => edgeVisible(edge, filter)) ?? [],
    [data, filter],
  );
  const connectedToHovered = useMemo(() => {
    const set = new Set<number>();
    if (hoveredNode === null) return set;
    set.add(hoveredNode);
    visibleEdges.forEach((edge) => {
      if (edge.source === hoveredNode) set.add(edge.target);
      if (edge.target === hoveredNode) set.add(edge.source);
    });
    return set;
  }, [hoveredNode, visibleEdges]);

  if (!open) return null;

  return (
    <div className="graph-overlay" role="dialog" aria-modal="true" aria-label="Graphe social global">
      <section className="graph-modal">
        <header className="graph-header">
          <div>
            <div className="eyebrow">Réseau social global</div>
            <h2>Relations entre les habitants</h2>
            <p>{data ? `${data.nodes.length} habitants · ${visibleEdges.length} liens affichés` : "Chargement…"}</p>
          </div>
          <div className="graph-actions">
            {([
              ["significant", "Liens significatifs"],
              ["conflicts", "Conflits"],
              ["all", "Tous les liens"],
            ] as Array<[GraphFilter, string]>).map(([value, label]) => (
              <button className={filter === value ? "active" : ""} key={value} onClick={() => setFilter(value)}>
                {label}
              </button>
            ))}
            <button onClick={onClose}>Fermer</button>
          </div>
        </header>

        <div className="graph-canvas-wrap">
          {loading && !data ? (
            <div className="graph-loading">Construction du réseau…</div>
          ) : (
            <svg className="social-graph" viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
              <g className="graph-edges">
                {visibleEdges.map((edge) => {
                  const source = positions.get(edge.source);
                  const target = positions.get(edge.target);
                  if (!source || !target) return null;
                  const dimmed = hoveredNode !== null && edge.source !== hoveredNode && edge.target !== hoveredNode;
                  return (
                    <line
                      className={`${edgeClass(edge)}${dimmed ? " graph-dimmed" : ""}`}
                      key={`${edge.source}-${edge.target}`}
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                    >
                      <title>{`Affection ${edge.affection.toFixed(0)} · Confiance ${edge.trust.toFixed(0)} · ${edge.conflictLabel}`}</title>
                    </line>
                  );
                })}
              </g>
              <g className="graph-nodes">
                {data?.nodes.map((node) => {
                  const position = positions.get(node.id);
                  if (!position) return null;
                  const conflict = node.rivalCount > 0;
                  const dimmed = hoveredNode !== null && !connectedToHovered.has(node.id);
                  return (
                    <g
                      className={`graph-node${conflict ? " graph-node-conflict" : ""}${selectedCitizenId === node.id ? " graph-node-selected" : ""}${dimmed ? " graph-dimmed" : ""}`}
                      key={node.id}
                      transform={`translate(${position.x} ${position.y})`}
                      onMouseEnter={() => setHoveredNode(node.id)}
                      onMouseLeave={() => setHoveredNode(null)}
                      onClick={() => onSelectCitizen(node.id)}
                    >
                      <circle r={5 + Math.min(5, node.friendCount * 0.7)} />
                      <title>{`${node.name} · ${node.friendCount} ami(s) · ${node.rivalCount} rival(aux) · ${node.temperament}`}</title>
                    </g>
                  );
                })}
              </g>
            </svg>
          )}
          <div className="graph-legend">
            <span><i className="graph-key graph-key-friend" /> Amitié</span>
            <span><i className="graph-key graph-key-close" /> Amitié proche</span>
            <span><i className="graph-key graph-key-rival" /> Tension / rivalité</span>
            <span><i className="graph-key graph-key-severe" /> Conflit grave</span>
          </div>
        </div>
      </section>
    </div>
  );
}
