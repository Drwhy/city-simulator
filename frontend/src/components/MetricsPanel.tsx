import { useMemo, useState } from "react";
import { buildMetricGroups, type CityStats, type MetricGroupId } from "../monitoring/metrics";
import "./MetricsPanel.css";

interface MetricsPanelProps {
  stats: CityStats | null;
}

const LOADING_METRICS = Array.from({ length: 6 }, (_, index) => ({
  id: `loading-${index}`,
  label: "Chargement",
  value: "…",
  tone: "neutral" as const,
}));

export function MetricsPanel({ stats }: MetricsPanelProps) {
  const [selected, setSelected] = useState<MetricGroupId>("summary");
  const groups = useMemo(() => (stats ? buildMetricGroups(stats) : []), [stats]);
  const active = groups.find((group) => group.id === selected) ?? groups[0];
  const metrics = active?.metrics ?? LOADING_METRICS;

  return (
    <section className="metrics-panel" aria-labelledby="metrics-title">
      <header className="metrics-toolbar">
        <div>
          <span className="eyebrow">Indicateurs</span>
          <strong id="metrics-title">{active?.label ?? "Chargement"}</strong>
        </div>
        <nav aria-label="Catégories d’indicateurs">
          {groups.map((group) => (
            <button
              className={group.id === active?.id ? "active" : ""}
              key={group.id}
              onClick={() => setSelected(group.id)}
              type="button"
            >
              {group.label}
            </button>
          ))}
        </nav>
      </header>
      <div className="metric-cards">
        {metrics.map((metric) => (
          <article className={`metric-card metric-${metric.tone}`} key={metric.id}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </div>
    </section>
  );
}