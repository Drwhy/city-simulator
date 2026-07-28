import { useMemo, useState } from "react";
import type { CityEvent } from "../types/city";

type EventFilter = "all" | "social" | "mobility" | "incidents" | "alerts";

const SOCIAL_TYPES = new Set([
  "positive_meeting",
  "friendship_formed",
  "rivalry_formed",
  "social_invitation_accepted",
  "social_gathering_started",
  "social_gathering_completed",
  "social_gathering_cancelled",
  "household_evening",
  "household_conflict",
  "social_tension",
]);

const MOBILITY_TYPES = new Set([
  "citizen_arrived",
  "bus_boarded",
  "bus_wait_abandoned",
  "traffic_congestion",
]);

const INCIDENT_TYPES = new Set([
  "theft",
  "dispute",
  "heated_dispute",
  "fight",
  "assault",
  "serious_assault",
  "police_dispatched",
  "police_arrived",
  "police_incident_resolved",
]);

function matchesFilter(event: CityEvent, filter: EventFilter): boolean {
  if (filter === "all") return true;
  if (filter === "social") return SOCIAL_TYPES.has(event.eventType);
  if (filter === "mobility") return MOBILITY_TYPES.has(event.eventType);
  if (filter === "incidents") return INCIDENT_TYPES.has(event.eventType) || event.incidentId !== null;
  return event.severity !== "info";
}

export function EventLog({
  events,
  onSelectIncident,
}: {
  events: CityEvent[];
  onSelectIncident: (incidentId: number) => void;
}) {
  const [filter, setFilter] = useState<EventFilter>("all");
  const visibleEvents = useMemo(
    () => [...events].reverse().filter((event) => matchesFilter(event, filter)).slice(0, 30),
    [events, filter],
  );

  return (
    <section className="event-log panel">
      <div className="section-heading event-log-heading">
        <div>
          <h2>Événements récents</h2>
          <span>{visibleEvents.length} affichés</span>
        </div>
        <div className="event-filters" aria-label="Filtrer les événements">
          {([
            ["all", "Tous"],
            ["social", "Social"],
            ["mobility", "Mobilité"],
            ["incidents", "Incidents"],
            ["alerts", "Alertes"],
          ] as Array<[EventFilter, string]>).map(([value, label]) => (
            <button
              className={filter === value ? "active" : ""}
              key={value}
              onClick={() => setFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="event-list">
        {visibleEvents.length === 0 ? (
          <p className="empty-events">Aucun événement dans cette catégorie.</p>
        ) : visibleEvents.map((event) => {
          const content = (
            <>
              <time>{event.time}</time>
              <p>{event.message}</p>
              {event.incidentId !== null && <span className="event-open-hint">Ouvrir</span>}
            </>
          );
          return event.incidentId !== null ? (
            <button
              className={`event event-action event-${event.severity}`}
              key={event.id}
              onClick={() => onSelectIncident(event.incidentId!)}
            >
              {content}
            </button>
          ) : (
            <article className={`event event-${event.severity}`} key={event.id}>
              {content}
            </article>
          );
        })}
      </div>
    </section>
  );
}
