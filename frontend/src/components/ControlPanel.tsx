import type { ChangeEvent } from "react";
import type { MapLayers } from "../hooks/useMapLayers";
import type { CitySnapshot } from "../types/city";
import { THEMATIC_OPTIONS, type ThematicLayer } from "../monitoring/neighborhoods";

interface ControlPanelProps {
  snapshot: CitySnapshot | null;
  layers: MapLayers;
  onToggleLayer: (key: keyof MapLayers, value: boolean) => void;
  onOpenBuilding: (id: number) => void;
  onOpenHousehold: (id: number) => void;
  onOpenSocialGraph: () => void;
  onOpenJustice: () => void;
  onOpenCrime: () => void;
  onOpenCommunications: () => void;
  thematicLayer: ThematicLayer;
  onThematicLayerChange: (layer: ThematicLayer) => void;
  onOpenNeighborhood: (id: number) => void;
  onOpenCitizen: (id: number) => void;
}

const LAYER_OPTIONS: Array<{ key: keyof MapLayers; label: string }> = [
  { key: "citizens", label: "Habitants" },
  { key: "buildings", label: "Bâtiments" },
  { key: "roads", label: "Réseau routier" },
  { key: "vehicles", label: "Véhicules" },
  { key: "transit", label: "Ligne et arrêts de bus" },
  { key: "traffic", label: "Congestion" },
  { key: "incidents", label: "Incidents" },
  { key: "social", label: "Liens sociaux" },
  { key: "health", label: "État de santé" },
  { key: "emergencies", label: "Urgences médicales" },
  { key: "ambulances", label: "Ambulances" },
  { key: "medicalFacilities", label: "Structures médicales" },
];

const LEGEND = [
  ["dot dot-walking", "Marche"],
  ["dot dot-driving", "Voiture"],
  ["dot dot-bus", "Bus / arrêt"],
  ["dot dot-police", "Police"],
  ["dot dot-health", "Santé / ambulance"],
  ["incident-legend", "Incident"],
  ["dot dot-working", "Travail"],
  ["dot dot-shopping", "Courses"],
  ["dot dot-sleeping", "Domicile"],
] as const;

function MobilityShare({ label, value, total }: { label: string; value: number; total: number }) {
  const percentage = total === 0 ? 0 : Math.round((value / total) * 100);
  return (
    <div className="mobility-share">
      <div><span>{label}</span><strong>{value} · {percentage} %</strong></div>
      <div className="share-track"><i style={{ width: `${percentage}%` }} /></div>
    </div>
  );
}

export function ControlPanel({
  snapshot,
  layers,
  onToggleLayer,
  onOpenBuilding,
  onOpenHousehold,
  onOpenSocialGraph,
  onOpenJustice,
  onOpenCrime,
  onOpenCommunications,
  thematicLayer,
  onThematicLayerChange,
  onOpenNeighborhood,
  onOpenCitizen,
}: ControlPanelProps) {
  const trips = snapshot?.stats.tripCountsToday ?? { walk: 0, car: 0, bus: 0 };
  const totalTrips = trips.walk + trips.car + trips.bus;
  const nextSocialEvent = snapshot?.social.events
    .slice()
    .sort((left, right) => left.plannedTick - right.plannedTick)[0] ?? null;
  const monitoredHousehold = snapshot?.housing.households.find(
    (household) => household.status !== "stable" || household.rentArrears > 0,
  ) ?? snapshot?.housing.households[0];

  return (
    <aside className="panel layers">
      <h2>Couches</h2>
      <div className="layer-options">
        {LAYER_OPTIONS.map(({ key, label }) => (
          <label key={key}>
            <input
              type="checkbox"
              checked={layers[key]}
              onChange={(event: ChangeEvent<HTMLInputElement>) =>
                onToggleLayer(key, event.target.checked)}
            /> {label}
          </label>
        ))}
      </div>

      <h3>Cartes thématiques</h3>
      <label className="thematic-select">Indicateur territorial<select value={thematicLayer} onChange={(event) => onThematicLayerChange(event.target.value as ThematicLayer)}>{THEMATIC_OPTIONS.map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <div className="neighborhood-shortcuts">{snapshot?.neighborhoods.neighborhoods.map((row) => <button key={row.id} onClick={() => onOpenNeighborhood(row.id)}><span>{row.name}</span><b>{Math.round(row.safetyPerception)} % sûr</b></button>)}</div>

      {snapshot?.health.hospital && (
        <button
          className="graph-open-button"
          onClick={() => onOpenBuilding(snapshot.health.hospital!.id)}
        >
          Ouvrir {snapshot.health.hospital.name}
        </button>
      )}
      {monitoredHousehold && (
        <button
          className="graph-open-button"
          onClick={() => onOpenHousehold(monitoredHousehold.id)}
        >
          Ouvrir le monitoring des foyers
        </button>
      )}

      <h3>Mobilité aujourd’hui</h3>
      <MobilityShare label="Marche" value={trips.walk} total={totalTrips} />
      <MobilityShare label="Voiture" value={trips.car} total={totalTrips} />
      <MobilityShare label="Bus" value={trips.bus} total={totalTrips} />

      <h3>Vie sociale</h3>
      <dl className="compact-metrics">
        <div><dt>Réseau moyen</dt><dd>{snapshot?.stats.averageSocialNetwork ?? 0}</dd></div>
        <div><dt>Habitants isolés</dt><dd>{snapshot?.stats.isolatedCitizens ?? 0}</dd></div>
        <div>
          <dt>Invitations acceptées</dt>
          <dd>{snapshot?.stats.socialAcceptancesToday ?? 0} / {snapshot?.stats.socialInvitationsToday ?? 0}</dd>
        </div>
      </dl>
      <button className="graph-open-button" onClick={onOpenSocialGraph}>
        Ouvrir le graphe social global
      </button>
      <h3>Communications</h3>
      <dl className="compact-metrics"><div><dt>Envoyées aujourd’hui</dt><dd>{snapshot?.stats.sentToday ?? 0}</dd></div><div><dt>Non lues</dt><dd>{snapshot?.stats.unreadCommunications ?? 0}</dd></div><div><dt>Réponses</dt><dd>{snapshot?.stats.communicationRepliesToday ?? 0}</dd></div></dl>
      <button className="graph-open-button" onClick={onOpenCommunications}>Ouvrir le monitoring des communications</button>
      <h3>Criminalité organisée</h3>
      <dl className="compact-metrics">
        <div><dt>Factions / membres</dt><dd>{snapshot?.crime.metrics.organizations ?? 0} / {snapshot?.crime.metrics.factionMembers ?? 0}</dd></div>
        <div><dt>Ventes illégales</dt><dd>{snapshot?.crime.metrics.illegalSalesToday ?? 0}</dd></div>
        <div><dt>Territoires disputés</dt><dd>{snapshot?.crime.metrics.contestedNeighborhoods ?? 0}</dd></div>
      </dl>
      <button className="graph-open-button" onClick={onOpenCrime}>Ouvrir le monitoring criminel</button>
      <h3>Justice</h3>
      <dl className="compact-metrics">
        <div><dt>Audiences</dt><dd>{snapshot?.stats.hearingsToday ?? 0} / {snapshot?.stats.courtCapacityToday ?? 0}</dd></div>
        <div><dt>Dossiers en attente</dt><dd>{snapshot?.stats.casesAwaitingHearing ?? 0}</dd></div>
        <div><dt>Peines actives</dt><dd>{snapshot?.stats.activeSentences ?? 0}</dd></div>
      </dl>
      <button className="graph-open-button" onClick={onOpenJustice}>
        Ouvrir le tribunal
      </button>
      {nextSocialEvent && (
        <button
          className="social-event-card"
          onClick={() => onOpenCitizen(nextSocialEvent.host.id)}
        >
          <strong>
            {nextSocialEvent.status === "active"
              ? "Rencontre en cours"
              : `Dans ${nextSocialEvent.minutesUntilStart} min`}
          </strong>
          <span>{nextSocialEvent.building.name}</span>
          <small>{nextSocialEvent.participants.length} participants</small>
        </button>
      )}

      <h3>Légende</h3>
      {LEGEND.map(([className, label]) => (
        <div className="legend" key={label}><i className={className} /> {label}</div>
      ))}
    </aside>
  );
}