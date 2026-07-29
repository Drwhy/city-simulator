import { sortCourtQueue } from "../monitoring/justice";
import type { JusticeOverview } from "../types/city";
import "./JusticeMonitoring.css";

interface JusticeModalProps {
  open: boolean;
  data: JusticeOverview | null;
  onClose: () => void;
  onSelectCase: (caseId: number) => void;
  onSelectCitizen: (citizenId: number) => void;
  onSelectBuilding: (buildingId: number) => void;
}

export function JusticeModal({ open, data, onClose, onSelectCase, onSelectCitizen, onSelectBuilding }: JusticeModalProps) {
  if (!open) return null;
  const metrics = data?.metrics;
  return (
    <div className="entity-modal-overlay" role="dialog" aria-modal="true" onMouseDown={onClose}>
      <section className="entity-modal-window justice-window" onMouseDown={(event) => event.stopPropagation()}>
        <button className="entity-modal-close" onClick={onClose}>Fermer</button>
        <div className="inspector-content">
          <div className="eyebrow">Institution judiciaire</div>
          <h2>Tribunal municipal</h2>
          {!data ? <p>Chargement…</p> : (
            <>
              <dl className="facts justice-metrics">
                <div><dt>Audiences du jour</dt><dd>{metrics?.hearingsToday} / {metrics?.courtCapacityToday}</dd></div>
                <div><dt>Personnel présent</dt><dd>{metrics?.courtStaffOnDuty}</dd></div>
                <div><dt>Dossiers en attente</dt><dd>{metrics?.casesAwaitingHearing}</dd></div>
                <div><dt>Peines actives</dt><dd>{metrics?.activeSentences}</dd></div>
                <div><dt>Probations</dt><dd>{metrics?.citizensOnProbation}</dd></div>
                <div><dt>Détenus</dt><dd>{metrics?.detainedCitizens} / {metrics?.detentionCapacity}</dd></div>
              </dl>
              <div className="justice-institution-links">
                {data.court && <button onClick={() => onSelectBuilding(data.court!.id)}>Inspecter le tribunal</button>}
                {data.detentionCenter && <button onClick={() => onSelectBuilding(data.detentionCenter!.id)}>Inspecter le centre de détention</button>}
              </div>
              <h3>File des audiences</h3>
              {data.queue.length === 0 ? <p className="muted">Aucun dossier en attente.</p> : (
                <div className="justice-list">
                  {sortCourtQueue(data.queue).map((row) => (
                    <button key={row.id} onClick={() => onSelectCase(row.id)}>
                      <span><strong>Dossier #{row.id}</strong><small>{row.charges.join(", ")}</small></span>
                      <b>Priorité {row.priority} · {Math.round(row.evidenceScore)} %</b>
                    </button>
                  ))}
                </div>
              )}
              <h3>Peines actives</h3>
              <div className="justice-list">
                {data.activeSentences.map((sentence) => (
                  <button key={sentence.id} onClick={() => sentence.citizen && onSelectCitizen(sentence.citizen.id)}>
                    <span><strong>{sentence.citizen?.name ?? "Habitant inconnu"}</strong><small>{sentence.label}</small></span>
                    <b>{sentence.status}</b>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  );
}