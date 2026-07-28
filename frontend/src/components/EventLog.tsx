import { useMemo, useState } from "react";
import type { CityEvent } from "../types/city";

type EventFilter = "all" | "economy" | "social" | "mobility" | "incidents" | "alerts";

const ECONOMY_TYPES = new Set([
  "vacancy_opened",
  "job_application_submitted",
  "employee_hired",
  "employee_dismissed",
  "employee_resigned",
  "business_closed",
  "salary_paid",
  "shopping_completed",
]);

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
  if (filter === "economy") return ECONOMY_TYPES.has(event.eventType);
  if (filter === "social") return SOCIAL_TYPES.has(event.eventType);
  if (filter === "mobility") return MOBILITY_TYPES.has(event.eventType);
  if (filter === "incidents") return INCIDENT_TYPES.has(event.eventType) || event.incidentId !== null;
  return event.severity !== "info";
}

export function EventLog({
  events,
  onSelectIncident,
  onSelectCitizen,
  onSelectBuilding,
}: {
  events: CityEvent[];
  onSelectIncident: (incidentId: number) => void;
  onSelectCitizen: (citizenId: number) => void;
  onSelectBuilding: (buildingId: number) => void;
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
            ["economy", "Économie"],
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
          const isEconomyEvent = ECONOMY_TYPES.has(event.eventType);
          const citizenId = isEconomyEvent ? (event.citizenIds[0] ?? null) : null;
          const buildingId = isEconomyEvent ? event.buildingId : null;
          const actionable = event.incidentId !== null || citizenId !== null || buildingId !== null;
          const content = (
            <>
              <time>{event.time}</time>
              <p>{event.message}</p>
              {actionable && <span className="event-open-hint">Ouvrir</span>}
            </>
          );
          return actionable ? (
            <button
              className={`event event-action event-${event.severity}`}
              key={event.id}
              onClick={() => {
                if (event.incidentId !== null) onSelectIncident(event.incidentId);
                else if (citizenId !== null) onSelectCitizen(citizenId);
                else if (buildingId !== null) onSelectBuilding(buildingId);
              }}
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
