import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import {
  getBuilding,
  getCitizen,
  getIncident,
  getVehicle,
  loadCity,
  pauseSimulation,
  resetCity,
  resumeSimulation,
  saveCity,
  setSimulationSpeed,
  stepSimulation,
} from "./api";
import { CitizenModal } from "./components/CitizenModal";
import { EntityModal } from "./components/EntityModal";
import { EventLog } from "./components/EventLog";
import { SocialGraph } from "./components/SocialGraph";
import { CityMap } from "./map/CityMap";
import { mergeCityMessage } from "./stream";
import type { CitySnapshot, CityStreamMessage, InspectorEntity, SelectedEntity } from "./types/city";

function websocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/city`;
}

const moneyFormatter = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});

function MobilityShare({ label, value, total }: { label: string; value: number; total: number }) {
  const percentage = total === 0 ? 0 : Math.round((value / total) * 100);
  return (
    <div className="mobility-share">
      <div><span>{label}</span><strong>{value} · {percentage} %</strong></div>
      <div className="share-track"><i style={{ width: `${percentage}%` }} /></div>
    </div>
  );
}

export default function App() {
  const [snapshot, setSnapshot] = useState<CitySnapshot | null>(null);
  const [connectionState, setConnectionState] = useState("Connexion…");
  const [selectedEntity, setSelectedEntity] = useState<SelectedEntity | null>(null);
  const [inspectorEntity, setInspectorEntity] = useState<InspectorEntity | null>(null);
  const [loadingEntity, setLoadingEntity] = useState(false);
  const [refreshingEntity, setRefreshingEntity] = useState(false);
  const [socialGraphOpen, setSocialGraphOpen] = useState(false);
  const [citizenModalId, setCitizenModalId] = useState<number | null>(null);
  const pausedRef = useRef(false);
  const selectedEntityRef = useRef<SelectedEntity | null>(null);
  const requestInFlightRef = useRef(false);

  const [showCitizens, setShowCitizens] = useState(true);
  const [showBuildings, setShowBuildings] = useState(true);
  const [showRoads, setShowRoads] = useState(true);
  const [showVehicles, setShowVehicles] = useState(true);
  const [showTransit, setShowTransit] = useState(true);
  const [showTraffic, setShowTraffic] = useState(true);
  const [showIncidents, setShowIncidents] = useState(true);
  const [showSocial, setShowSocial] = useState(true);
  const [showHealth, setShowHealth] = useState(true);
  const [showEmergencies, setShowEmergencies] = useState(true);
  const [showAmbulances, setShowAmbulances] = useState(true);
  const [showMedicalFacilities, setShowMedicalFacilities] = useState(true);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let disposed = false;

    const connect = () => {
      setConnectionState("Connexion…");
      socket = new WebSocket(websocketUrl());
      socket.onopen = () => setConnectionState("Connecté");
      socket.onmessage = (message) => {
        const data = JSON.parse(message.data) as CityStreamMessage;
        setSnapshot((current) => mergeCityMessage(current, data));
      };
      socket.onerror = () => setConnectionState("Erreur de connexion");
      socket.onclose = () => {
        if (disposed) return;
        setConnectionState("Reconnexion…");
        reconnectTimer = window.setTimeout(connect, 1200);
      };
    };

    connect();
    return () => {
      disposed = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  const selectCitizen = useCallback((citizenId: number) => {
    setSelectedEntity({ kind: "citizen", id: citizenId });
    setCitizenModalId(citizenId);
  }, []);

  const selectVehicle = useCallback((vehicleId: number) => {
    setCitizenModalId(null);
    setSelectedEntity({ kind: "vehicle", id: vehicleId });
  }, []);

  const selectIncident = useCallback((incidentId: number) => {
    setCitizenModalId(null);
    setSelectedEntity({ kind: "incident", id: incidentId });
  }, []);

  const selectBuilding = useCallback((buildingId: number) => {
    setCitizenModalId(null);
    setSelectedEntity({ kind: "building", id: buildingId });
  }, []);

  const handleCitizenData = useCallback((data: Extract<InspectorEntity, { kind: "citizen" }>) => {
    const current = selectedEntityRef.current;
    if (current?.kind === "citizen" && current.id === data.id) setInspectorEntity(data);
  }, []);

  useEffect(() => {
    pausedRef.current = snapshot?.simulation.paused ?? false;
  }, [snapshot?.simulation.paused]);

  useEffect(() => {
    selectedEntityRef.current = selectedEntity;
  }, [selectedEntity]);

  const refreshSelectedEntity = useCallback(async (initial: boolean) => {
    const selection = selectedEntityRef.current;
    // La fiche citoyen est l'unique propriétaire de /api/citizens/{id}.
    // Cela évite un double polling depuis App et depuis la modale.
    if (!selection || selection.kind === "citizen" || requestInFlightRef.current) return;
    const requestKey = `${selection.kind}:${selection.id}`;
    requestInFlightRef.current = true;
    if (initial) {
      setLoadingEntity(true);
      setInspectorEntity(null);
    } else {
      setRefreshingEntity(true);
    }
    try {
      const entity = selection.kind === "vehicle"
        ? await getVehicle(selection.id)
        : selection.kind === "incident"
          ? await getIncident(selection.id)
          : await getBuilding(selection.id);
      const current = selectedEntityRef.current;
      if (current && `${current.kind}:${current.id}` === requestKey) setInspectorEntity(entity);
    } catch {
      const current = selectedEntityRef.current;
      if (initial && current && `${current.kind}:${current.id}` === requestKey) setInspectorEntity(null);
    } finally {
      requestInFlightRef.current = false;
      setLoadingEntity(false);
      setRefreshingEntity(false);
    }
  }, []);

  useEffect(() => {
    requestInFlightRef.current = false;
    if (!selectedEntity) {
      setInspectorEntity(null);
      setLoadingEntity(false);
      setRefreshingEntity(false);
      return;
    }
    if (selectedEntity.kind === "citizen") {
      // CitizenModal récupère et pousse les données vers App via onData.
      if (inspectorEntity?.kind !== "citizen" || inspectorEntity.id !== selectedEntity.id) {
        setInspectorEntity(null);
      }
      return;
    }
    void refreshSelectedEntity(true);
    const refreshTimer = window.setInterval(() => {
      if (!pausedRef.current) void refreshSelectedEntity(false);
    }, 1200);
    return () => window.clearInterval(refreshTimer);
  }, [selectedEntity, refreshSelectedEntity]);

  useEffect(() => {
    if (snapshot?.simulation.paused && selectedEntity && selectedEntity.kind !== "citizen") {
      // En pause, une actualisation ne se produit qu'après un pas manuel (tick modifié).
      void refreshSelectedEntity(false);
    }
  }, [snapshot?.tick, snapshot?.simulation.paused, selectedEntity, refreshSelectedEntity]);

  const activities = useMemo(() => snapshot?.stats.activityCounts ?? {}, [snapshot]);
  const trips = snapshot?.stats.tripCountsToday ?? { walk: 0, car: 0, bus: 0 };
  const totalTrips = trips.walk + trips.car + trips.bus;
  const selectedRelationships = inspectorEntity?.kind === "citizen"
    ? inspectorEntity.relationships.map((relationship) => ({
        citizenId: relationship.citizenId,
        status: relationship.status,
        affection: relationship.affection,
      }))
    : [];
  const nextSocialEvent = snapshot?.social.events
    .slice()
    .sort((a, b) => a.plannedTick - b.plannedTick)[0] ?? null;
  const modalEntity = selectedEntity && selectedEntity.kind !== "citizen"
    && inspectorEntity?.kind === selectedEntity.kind
    && inspectorEntity.id === selectedEntity.id
    ? inspectorEntity
    : null;
  const selectedLabel = inspectorEntity?.kind === "citizen"
    ? inspectorEntity.name
    : inspectorEntity?.kind === "vehicle"
      ? `${inspectorEntity.type === "police" ? "Unité de police" : inspectorEntity.type === "ambulance" ? "Ambulance" : inspectorEntity.type === "bus" ? "Bus" : "Véhicule"} #${inspectorEntity.id}`
      : inspectorEntity?.kind === "incident"
        ? inspectorEntity.title
        : inspectorEntity?.kind === "building"
          ? inspectorEntity.name
          : selectedEntity ? `${selectedEntity.kind} #${selectedEntity.id}` : "Aucune sélection";

  async function togglePause() {
    if (!snapshot) return;
    if (snapshot.simulation.paused) await resumeSimulation();
    else await pauseSimulation();
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">Monitoring urbain · v0.8</div>
          <h1>City Simulator</h1>
        </div>
        <div className="time-block">
          <strong>{snapshot?.timeLabel ?? "Chargement…"}</strong>
          <span>{connectionState}</span>
        </div>
        <div className="controls">
          <button onClick={togglePause}>{snapshot?.simulation.paused ? "▶ Reprendre" : "⏸ Pause"}</button>
          {[1, 5, 20, 60].map((speed) => (
            <button
              className={snapshot?.simulation.speed === speed ? "active" : ""}
              key={speed}
              onClick={() => setSimulationSpeed(speed)}
            >
              ×{speed}
            </button>
          ))}
          <button onClick={() => stepSimulation(60)}>+1 h</button>
          <button onClick={() => saveCity()}>Sauvegarder</button>
          <button disabled={!snapshot?.simulation.hasSave} onClick={() => loadCity()}>Charger</button>
          <button className="danger-button" onClick={() => resetCity()}>Réinitialiser</button>
        </div>
      </header>

      <section className="stats-grid">
        <div className="stat-card health-stat"><span>Urgences médicales</span><strong>{snapshot?.stats.medicalEmergencies ?? 0}</strong></div>
        <div className="stat-card health-stat"><span>File d’attente médicale</span><strong>{snapshot?.stats.patientsWaiting ?? 0}</strong></div>
        <div className="stat-card health-stat"><span>Hospitalisés</span><strong>{snapshot?.stats.hospitalizedPatients ?? 0} / {snapshot?.stats.hospitalBeds ?? 0}</strong></div>
        <div className="stat-card health-stat"><span>Soignants en service</span><strong>{snapshot?.stats.medicalStaffOnDuty ?? 0}</strong></div>
        <div className="stat-card health-stat"><span>Ambulances disponibles</span><strong>{snapshot?.stats.ambulancesAvailable ?? 0}</strong></div>
        <div className="stat-card health-stat"><span>Attente médicale moyenne</span><strong>{snapshot?.stats.averageMedicalWaitMinutes ?? 0} min</strong></div>
        <div className="stat-card"><span>Population</span><strong>{snapshot?.stats.population ?? 0}</strong></div>
        <div className="stat-card"><span>Argent moyen</span><strong>{moneyFormatter.format(snapshot?.stats.averageMoney ?? 0)}</strong></div>
        <div className="stat-card"><span>Travailleurs en service</span><strong>{snapshot?.stats.workersOnDuty ?? 0} / {snapshot?.stats.employedCitizens ?? 0}</strong></div>
        <div className="stat-card"><span>Performance moyenne</span><strong>{snapshot?.stats.averageJobPerformance ?? 0} %</strong></div>
        <div className="stat-card economy-stat"><span>Taux de chômage</span><strong>{snapshot?.stats.unemploymentRate ?? 0} %</strong></div>
        <div className="stat-card economy-stat"><span>Postes vacants</span><strong>{snapshot?.stats.openPositions ?? 0}</strong></div>
        <div className="stat-card economy-stat"><span>Entreprises déficitaires</span><strong>{snapshot?.stats.deficitBusinesses ?? 0}</strong></div>
        <div className="stat-card economy-stat"><span>Salaire médian</span><strong>{moneyFormatter.format(snapshot?.stats.medianSalary ?? 0)}</strong></div>
        <div className="stat-card economy-stat"><span>Revenu médian des foyers</span><strong>{moneyFormatter.format(snapshot?.stats.medianHouseholdIncome ?? 0)}</strong></div>
        <div className="stat-card economy-stat"><span>Recrutements aujourd’hui</span><strong>{snapshot?.stats.hiresToday ?? 0}</strong></div>
        <div className="stat-card economy-stat"><span>Licenciements aujourd’hui</span><strong>{snapshot?.stats.layoffsToday ?? 0}</strong></div>
        <div className="stat-card"><span>Courses aujourd’hui</span><strong>{snapshot?.stats.shoppingTripsToday ?? 0}</strong></div>
        <div className="stat-card"><span>Ventes du marché</span><strong>{moneyFormatter.format(snapshot?.stats.shopSalesToday ?? 0)}</strong></div>
        <div className="stat-card"><span>En déplacement</span><strong>{(activities.walking ?? 0) + (activities.driving ?? 0) + (activities.riding_bus ?? 0) + (activities.waiting_bus ?? 0)}</strong></div>
        <div className="stat-card"><span>Véhicules actifs</span><strong>{snapshot?.stats.movingVehicles ?? 0}</strong></div>
        <div className="stat-card"><span>Passagers bus</span><strong>{snapshot?.stats.busPassengers ?? 0}</strong></div>
        <div className="stat-card"><span>Montées bus</span><strong>{snapshot?.stats.busBoardingsToday ?? 0}</strong></div>
        <div className="stat-card"><span>Retard trafic</span><strong>{snapshot?.stats.trafficDelayToday ?? 0} min</strong></div>
        <div className="stat-card"><span>Trajet moyen</span><strong>{snapshot?.stats.averageTripMinutes ?? 0} min</strong></div>
        <div className="stat-card"><span>Amitiés</span><strong>{snapshot?.stats.friendships ?? 0}</strong></div>
        <div className="stat-card"><span>Rivalités</span><strong>{snapshot?.stats.rivalries ?? 0}</strong></div>
        <div className="stat-card"><span>Rencontres prévues</span><strong>{snapshot?.stats.activeSocialEvents ?? 0}</strong></div>
        <div className="stat-card"><span>Cohésion des foyers</span><strong>{snapshot?.stats.averageHouseholdCohesion ?? 0} %</strong></div>
        <div className="stat-card"><span>Incidents actifs</span><strong>{snapshot?.stats.activeIncidents ?? 0}</strong></div>
        <div className="stat-card"><span>Incidents graves</span><strong>{snapshot?.stats.seriousIncidents ?? 0}</strong></div>
        <div className="stat-card"><span>Police disponible</span><strong>{snapshot?.stats.policeUnitsAvailable ?? 0}</strong></div>
        <div className="stat-card"><span>Agents en service</span><strong>{snapshot?.stats.policeOfficersOnDuty ?? 0}</strong></div>
        <div className="stat-card"><span>Mesures immédiates</span><strong>{(snapshot?.stats.policeWarningsToday ?? 0) + (snapshot?.stats.policeDetentionsToday ?? 0)}</strong></div>
        <div className="stat-card"><span>Réponse police</span><strong>{snapshot?.stats.averagePoliceResponseMinutes ?? 0} min</strong></div>
        <div className="stat-card"><span>Enquêtes ouvertes</span><strong>{snapshot?.stats.openInvestigations ?? 0}</strong></div>
        <div className="stat-card"><span>Suspects identifiés</span><strong>{snapshot?.stats.suspectsIdentified ?? 0}</strong></div>
        <div className="stat-card"><span>Arrestations du jour</span><strong>{snapshot?.stats.arrestsToday ?? 0}</strong></div>
        <div className="stat-card"><span>Audiences en attente</span><strong>{snapshot?.stats.casesAwaitingHearing ?? 0}</strong></div>
      </section>

      <section className="workspace">
        <aside className="panel layers">
          <h2>Couches</h2>
          <label><input type="checkbox" checked={showCitizens} onChange={(event: ChangeEvent<HTMLInputElement>) => setShowCitizens(event.target.checked)} /> Habitants</label>
          <label><input type="checkbox" checked={showBuildings} onChange={(event: ChangeEvent<HTMLInputElement>) => setShowBuildings(event.target.checked)} /> Bâtiments</label>
          <label><input type="checkbox" checked={showRoads} onChange={(event: ChangeEvent<HTMLInputElement>) => setShowRoads(event.target.checked)} /> Réseau routier</label>
          <label><input type="checkbox" checked={showVehicles} onChange={(event: ChangeEvent<HTMLInputElement>) => setShowVehicles(event.target.checked)} /> Véhicules</label>
          <label><input type="checkbox" checked={showTransit} onChange={(event: ChangeEvent<HTMLInputElement>) => setShowTransit(event.target.checked)} /> Ligne et arrêts de bus</label>
          <label><input type="checkbox" checked={showTraffic} onChange={(event: ChangeEvent<HTMLInputElement>) => setShowTraffic(event.target.checked)} /> Congestion</label>
          <label><input type="checkbox" checked={showIncidents} onChange={(event: ChangeEvent<HTMLInputElement>) => setShowIncidents(event.target.checked)} /> Incidents</label>
          <label><input type="checkbox" checked={showSocial} onChange={(event: ChangeEvent<HTMLInputElement>) => setShowSocial(event.target.checked)} /> Liens sociaux</label>
          <label><input type="checkbox" checked={showHealth} onChange={(event: ChangeEvent<HTMLInputElement>) => setShowHealth(event.target.checked)} /> État de santé</label>
          <label><input type="checkbox" checked={showEmergencies} onChange={(event: ChangeEvent<HTMLInputElement>) => setShowEmergencies(event.target.checked)} /> Urgences médicales</label>
          <label><input type="checkbox" checked={showAmbulances} onChange={(event: ChangeEvent<HTMLInputElement>) => setShowAmbulances(event.target.checked)} /> Ambulances</label>
          <label><input type="checkbox" checked={showMedicalFacilities} onChange={(event: ChangeEvent<HTMLInputElement>) => setShowMedicalFacilities(event.target.checked)} /> Structures médicales</label>
          {snapshot?.health.hospital && <button className="graph-open-button" onClick={() => selectBuilding(snapshot.health.hospital!.id)}>Ouvrir {snapshot.health.hospital.name}</button>}

          <h3>Mobilité aujourd’hui</h3>
          <MobilityShare label="Marche" value={trips.walk} total={totalTrips} />
          <MobilityShare label="Voiture" value={trips.car} total={totalTrips} />
          <MobilityShare label="Bus" value={trips.bus} total={totalTrips} />

          <h3>Vie sociale</h3>
          <dl className="compact-metrics">
            <div><dt>Réseau moyen</dt><dd>{snapshot?.stats.averageSocialNetwork ?? 0}</dd></div>
            <div><dt>Habitants isolés</dt><dd>{snapshot?.stats.isolatedCitizens ?? 0}</dd></div>
            <div><dt>Invitations acceptées</dt><dd>{snapshot?.stats.socialAcceptancesToday ?? 0} / {snapshot?.stats.socialInvitationsToday ?? 0}</dd></div>
          </dl>
          <button className="graph-open-button" onClick={() => setSocialGraphOpen(true)}>
            Ouvrir le graphe social global
          </button>

          {nextSocialEvent && (
            <button className="social-event-card" onClick={() => selectCitizen(nextSocialEvent.host.id)}>
              <strong>{nextSocialEvent.status === "active" ? "Rencontre en cours" : `Dans ${nextSocialEvent.minutesUntilStart} min`}</strong>
              <span>{nextSocialEvent.building.name}</span>
              <small>{nextSocialEvent.participants.length} participants</small>
            </button>
          )}

          <h3>Légende</h3>
          <div className="legend"><i className="dot dot-walking" /> Marche</div>
          <div className="legend"><i className="dot dot-driving" /> Voiture</div>
          <div className="legend"><i className="dot dot-bus" /> Bus / arrêt</div>
          <div className="legend"><i className="dot dot-police" /> Police</div>
          <div className="legend"><i className="dot dot-health" /> Santé / ambulance</div>
          <div className="legend"><i className="incident-legend" /> Incident</div>
          <div className="legend"><i className="dot dot-working" /> Travail</div>
          <div className="legend"><i className="dot dot-shopping" /> Courses</div>
          <div className="legend"><i className="dot dot-sleeping" /> Domicile</div>

          <h3>Inspection</h3>
          <p className="muted">Cliquez sur un habitant, un véhicule ou un incident. La carte et la fiche restent stables pendant les actualisations.</p>
        </aside>

        <CityMap
          snapshot={snapshot}
          selectedEntity={selectedEntity}
          onSelectCitizen={selectCitizen}
          onSelectVehicle={selectVehicle}
          onSelectIncident={selectIncident}
          onSelectBuilding={selectBuilding}
          showCitizens={showCitizens}
          showBuildings={showBuildings}
          showRoads={showRoads}
          showVehicles={showVehicles}
          showTransit={showTransit}
          showTraffic={showTraffic}
          showIncidents={showIncidents}
          showSocial={showSocial}
          showHealth={showHealth}
          showEmergencies={showEmergencies}
          showAmbulances={showAmbulances}
          showMedicalFacilities={showMedicalFacilities}
          selectedRelationships={selectedRelationships}
        />

        <aside className="panel selection-panel">
          <h2>Inspection</h2>
          <p className="muted">Chaque habitant, véhicule, incident ou bâtiment s’ouvre dans une fenêtre complète et cohérente.</p>
          {selectedEntity ? (
            <div className="selection-summary">
              <strong>{selectedLabel}</strong>
              <span>{refreshingEntity ? "Actualisation…" : snapshot?.simulation.paused ? "Données figées — simulation en pause" : "Suivi en direct"}</span>
              <button onClick={() => selectedEntity.kind === "citizen" ? setCitizenModalId(selectedEntity.id) : void refreshSelectedEntity(false)}>Rouvrir la fiche</button>
            </div>
          ) : <p>Sélectionnez un élément sur la carte.</p>}
        </aside>
      </section>

      <EventLog
        events={snapshot?.events ?? []}
        onSelectIncident={selectIncident}
        onSelectCitizen={selectCitizen}
        onSelectBuilding={selectBuilding}
      />
      <SocialGraph
        open={socialGraphOpen}
        onClose={() => setSocialGraphOpen(false)}
        onSelectCitizen={selectCitizen}
        selectedCitizenId={citizenModalId}
        paused={snapshot?.simulation.paused ?? false}
        snapshotTick={snapshot?.tick ?? 0}
      />
      <EntityModal
        entity={modalEntity}
        loading={Boolean(selectedEntity && selectedEntity.kind !== "citizen" && loadingEntity)}
        refreshing={refreshingEntity}
        paused={snapshot?.simulation.paused ?? false}
        onClose={() => setSelectedEntity(null)}
        onSelectCitizen={selectCitizen}
        onSelectVehicle={selectVehicle}
        onSelectIncident={selectIncident}
      />
      <CitizenModal
        citizenId={citizenModalId}
        paused={snapshot?.simulation.paused ?? false}
        snapshotTick={snapshot?.tick ?? 0}
        graphContext={socialGraphOpen}
        onClose={() => setCitizenModalId(null)}
        onSelectCitizen={selectCitizen}
        onData={handleCitizenData}
        onSelectIncident={(incidentId) => {
          setCitizenModalId(null);
          setSocialGraphOpen(false);
          selectIncident(incidentId);
        }}
      />
    </main>
  );
}
