import { useEffect, useState } from "react";
import { getCase } from "../api";
import type { JudicialCaseDetail } from "../types/city";
import "./JusticeMonitoring.css";

interface CaseModalProps {
  caseId: number | null;
  paused: boolean;
  snapshotTick: number;
  onClose: () => void;
  onSelectCitizen: (citizenId: number) => void;
  onSelectIncident: (incidentId: number) => void;
}

export function CaseModal({ caseId, paused, snapshotTick, onClose, onSelectCitizen, onSelectIncident }: CaseModalProps) {
  const [data, setData] = useState<JudicialCaseDetail | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (caseId === null) { setData(null); return; }
    let live = true;
    setRefreshing(true);
    getCase(caseId)
      .then((row) => { if (live) setData(row); })
      .finally(() => { if (live) setRefreshing(false); });
    return () => { live = false; };
  }, [caseId, paused ? 0 : snapshotTick]);

  if (caseId === null) return null;
  return (
    <div className="entity-modal-overlay nested-entity-modal" role="dialog" aria-modal="true" onMouseDown={onClose}>
      <section className="entity-modal-window justice-window" onMouseDown={(event) => event.stopPropagation()}>
        <button className="entity-modal-close" onClick={onClose}>Fermer</button>
        <div className="inspector-content">
          <div className="eyebrow">Dossier judiciaire #{caseId}</div>
          <h2>{data?.charges.join(" · ") ?? "Chargement…"}</h2>
          {refreshing && data && <span className="live-status refreshing"><i />Actualisation</span>}
          {data && (
            <>
              <p className={`business-status case-status-${data.status}`}>{data.status}</p>
              <dl className="facts">
                <div><dt>Prévenu</dt><dd><button onClick={() => data.defendant && onSelectCitizen(data.defendant.id)}>{data.defendant?.name ?? "Inconnu"}</button></dd></div>
                <div><dt>Décision du parquet</dt><dd>{data.prosecutorDecision ?? "En attente"}</dd></div>
                <div><dt>Solidité des preuves</dt><dd>{Math.round(data.evidenceScore)} %</dd></div>
                <div><dt>Reports</dt><dd>{data.delayCount}</dd></div>
                <div><dt>Verdict</dt><dd>{data.verdict ?? "—"}</dd></div>
                <div><dt>Peine</dt><dd>{data.sentence ?? "—"}</dd></div>
              </dl>
              <button className="entity-link" onClick={() => onSelectIncident(data.incidentId)}>Ouvrir l’incident #{data.incidentId}</button>
              <h3>Chronologie complète</h3>
              <div className="justice-timeline">
                {data.timeline.map((entry, index) => (
                  <article key={`${entry.tick}-${entry.eventType}-${index}`}>
                    <strong>{entry.label}</strong><span>{entry.detail}</span><small>Tick {entry.tick}</small>
                  </article>
                ))}
              </div>
              <h3>Peines structurées</h3>
              <div className="justice-list">
                {data.sentences.map((sentence) => (
                  <article key={sentence.id}>
                    <strong>{sentence.label}</strong>
                    <span>{sentence.status}{sentence.requiredMinutes ? ` · ${sentence.completedMinutes}/${sentence.requiredMinutes} min` : ""}</span>
                    {sentence.beneficiary && <small>Bénéficiaire : {sentence.beneficiary.name}</small>}
                  </article>
                ))}
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  );
}