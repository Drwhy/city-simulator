import { useCallback, useEffect, useRef, useState } from "react";
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
import { CaseModal } from "./components/CaseModal";
import { CitizenModal } from "./components/CitizenModal";
import { CommunicationModal } from "./components/CommunicationModal";
import { CrimeMonitoring } from "./components/CrimeMonitoring";
import { EntityModal } from "./components/EntityModal";
import { HouseholdModal } from "./components/HouseholdModal";
import { JusticeModal } from "./components/JusticeModal";
import { MetricsPanel } from "./components/MetricsPanel";
import { NeighborhoodModal } from "./components/NeighborhoodModal";
import { ControlPanel } from "./components/ControlPanel";
import { EventLog } from "./components/EventLog";
import { SocialGraph } from "./components/SocialGraph";
import { CityMap } from "./map/CityMap";
import { useCityStream } from "./hooks/useCityStream";
import { useMapLayers } from "./hooks/useMapLayers";
import type { InspectorEntity, SelectedEntity } from "./types/city";
import type { ThematicLayer } from "./monitoring/neighborhoods";

export default function App() {
  const { snapshot, connectionState } = useCityStream();
  const [selectedEntity, setSelectedEntity] = useState<SelectedEntity | null>(null);
  const [inspectorEntity, setInspectorEntity] = useState<InspectorEntity | null>(null);
  const [loadingEntity, setLoadingEntity] = useState(false);
  const [refreshingEntity, setRefreshingEntity] = useState(false);
  const [socialGraphOpen, setSocialGraphOpen] = useState(false);
  const [citizenModalId, setCitizenModalId] = useState<number | null>(null);
  const [householdModalId, setHouseholdModalId] = useState<number | null>(null);
  const [justiceModalOpen, setJusticeModalOpen] = useState(false);
  const [communicationModalOpen, setCommunicationModalOpen] = useState(false);
  const [crimeMonitoringOpen, setCrimeMonitoringOpen] = useState(false);
  const [neighborhoodModalId, setNeighborhoodModalId] = useState<number | null>(null);
  const [thematicLayer, setThematicLayer] = useState<ThematicLayer>("none");
  const [caseModalId, setCaseModalId] = useState<number | null>(null);
  const [citizenCount, setCitizenCount] = useState(250);
  const pausedRef = useRef(false);
  const selectedEntityRef = useRef<SelectedEntity | null>(null);
  const requestInFlightRef = useRef(false);

  const { layers, toggleLayer } = useMapLayers();



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

  const selectedRelationships = inspectorEntity?.kind === "citizen"
    ? inspectorEntity.relationships.map((relationship) => ({
        citizenId: relationship.citizenId,
        status: relationship.status,
        affection: relationship.affection,
      }))
    : [];
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
          <div className="eyebrow">Monitoring urbain · v0.13</div>
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
          <label className="population-control">Population
            <select value={citizenCount} onChange={(event) => setCitizenCount(Number(event.target.value))}>
              {[100, 250, 500, 1000, 2500, 5000].map((count) => <option key={count} value={count}>{count}</option>)}
            </select>
          </label>
          <button className="danger-button" onClick={() => resetCity(12345, citizenCount)}>Réinitialiser</button>
        </div>
      </header>

      <MetricsPanel stats={snapshot?.stats ?? null} />

      <section className="workspace">
        <ControlPanel snapshot={snapshot} layers={layers} onToggleLayer={toggleLayer} onOpenBuilding={selectBuilding} onOpenHousehold={setHouseholdModalId} onOpenSocialGraph={() => setSocialGraphOpen(true)} onOpenJustice={() => setJusticeModalOpen(true)} onOpenCommunications={() => setCommunicationModalOpen(true)} onOpenCrime={() => setCrimeMonitoringOpen(true)} thematicLayer={thematicLayer} onThematicLayerChange={setThematicLayer} onOpenNeighborhood={setNeighborhoodModalId} onOpenCitizen={selectCitizen} />

        <CityMap
          snapshot={snapshot}
          selectedEntity={selectedEntity}
          onSelectCitizen={selectCitizen}
          onSelectVehicle={selectVehicle}
          onSelectIncident={selectIncident}
          onSelectBuilding={selectBuilding}
          onSelectNeighborhood={setNeighborhoodModalId}
          thematicLayer={thematicLayer}
          showCitizens={layers.citizens}
          showBuildings={layers.buildings}
          showRoads={layers.roads}
          showVehicles={layers.vehicles}
          showTransit={layers.transit}
          showTraffic={layers.traffic}
          showIncidents={layers.incidents}
          showSocial={layers.social}
          showHealth={layers.health}
          showEmergencies={layers.emergencies}
          showAmbulances={layers.ambulances}
          showMedicalFacilities={layers.medicalFacilities}
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
        onSelectHousehold={setHouseholdModalId}
      />
      <NeighborhoodModal neighborhoodId={neighborhoodModalId} paused={snapshot?.simulation.paused ?? false} snapshotTick={snapshot?.tick ?? 0} onClose={() => setNeighborhoodModalId(null)} onSelectBuilding={(id) => { setNeighborhoodModalId(null); selectBuilding(id); }} onSelectIncident={(id) => { setNeighborhoodModalId(null); selectIncident(id); }} onSelectVehicle={(id) => { setNeighborhoodModalId(null); selectVehicle(id); }} />
      <CommunicationModal open={communicationModalOpen} data={snapshot?.communications ?? null} onClose={() => setCommunicationModalOpen(false)} onSelectCitizen={(id) => { setCommunicationModalOpen(false); selectCitizen(id); }} />
      <CrimeMonitoring
        open={crimeMonitoringOpen}
        data={snapshot?.crime ?? null}
        onClose={() => setCrimeMonitoringOpen(false)}
        onSelectCitizen={(id) => { setCrimeMonitoringOpen(false); selectCitizen(id); }}
        onSelectIncident={(id) => { setCrimeMonitoringOpen(false); selectIncident(id); }}
        onSelectNeighborhood={(id) => { setCrimeMonitoringOpen(false); setNeighborhoodModalId(id); }}
      />
      <JusticeModal
        open={justiceModalOpen}
        data={snapshot?.justice ?? null}
        onClose={() => setJusticeModalOpen(false)}
        onSelectCase={setCaseModalId}
        onSelectCitizen={(id) => { setJusticeModalOpen(false); selectCitizen(id); }}
        onSelectBuilding={(id) => { setJusticeModalOpen(false); selectBuilding(id); }}
      />
      <CaseModal
        caseId={caseModalId}
        paused={snapshot?.simulation.paused ?? false}
        snapshotTick={snapshot?.tick ?? 0}
        onClose={() => setCaseModalId(null)}
        onSelectCitizen={(id) => { setCaseModalId(null); selectCitizen(id); }}
        onSelectIncident={(id) => { setCaseModalId(null); selectIncident(id); }}
      />
      <HouseholdModal householdId={householdModalId} paused={snapshot?.simulation.paused ?? false} snapshotTick={snapshot?.tick ?? 0} onClose={() => setHouseholdModalId(null)} onSelectCitizen={(id) => { setHouseholdModalId(null); selectCitizen(id); }} />
      <CitizenModal
        citizenId={citizenModalId}
        paused={snapshot?.simulation.paused ?? false}
        snapshotTick={snapshot?.tick ?? 0}
        graphContext={socialGraphOpen}
        onClose={() => setCitizenModalId(null)}
        onSelectCitizen={selectCitizen}
        onData={handleCitizenData}
        onSelectCase={setCaseModalId}
        onSelectIncident={(incidentId) => {
          setCitizenModalId(null);
          setSocialGraphOpen(false);
          selectIncident(incidentId);
        }}
      />
    </main>
  );
}
