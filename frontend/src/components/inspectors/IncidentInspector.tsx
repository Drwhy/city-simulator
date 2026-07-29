import type { IncidentDetail } from "../../types/city";
export function IncidentInspector({
  incident,
  onSelectCitizen,
  onSelectVehicle,
}: {
  incident: IncidentDetail;
  onSelectCitizen: (citizenId: number) => void;
  onSelectVehicle: (vehicleId: number) => void;
}) {
  const statusLabels: Record<string, string> = {
    active: "Actif, non signalé",
    reported: "Signalé",
    responding: "Police en route",
    on_scene: "Police sur place",
    resolved: "Résolu",
    expired: "Archivé",
  };
  const involved = incident.involved.filter((person): person is { id: number; name: string } => person !== null);
  const witnesses = incident.witnesses.filter((person): person is { id: number; name: string } => person !== null);
  return (
    <div className="inspector-content incident-inspector">
      <div className="eyebrow">Incident #{incident.id}</div>
      <h2>{incident.title}</h2>
      <p className={`incident-severity incident-severity-${incident.severity}`}>
        {incident.severity === "danger" ? "Grave" : "À surveiller"} · {statusLabels[incident.status] ?? incident.status}
      </p>
      <p className="incident-description">{incident.description}</p>

      <dl className="facts">
        <div><dt>Lieu</dt><dd>{incident.building?.name ?? `Case ${incident.x}, ${incident.y}`}</dd></div>
        <div><dt>Signalé</dt><dd>{incident.reported ? "Oui" : "Non"}</dd></div>
        <div><dt>Visible encore</dt><dd>{incident.remainingMinutes} min</dd></div>
        <div><dt>Niveau conflit</dt><dd>{incident.conflictLevel || "—"}</dd></div>
      </dl>

      {incident.offender && (
        <button className="entity-link danger-link" onClick={() => onSelectCitizen(incident.offender!.id)}>
          Auteur présumé : {incident.offender.name}
        </button>
      )}

      {incident.victims.length > 0 && <h3>Victimes</h3>}
      <div className="passenger-list">
        {incident.victims.filter((person): person is { id: number; name: string } => person !== null).map((person) => (
          <button key={person.id} onClick={() => onSelectCitizen(person.id)}>{person.name}</button>
        ))}
      </div>

      <h3>Personnes impliquées</h3>
      <div className="passenger-list">
        {involved.slice(0, 10).map((person) => (
          <button key={person.id} onClick={() => onSelectCitizen(person.id)}>{person.name}</button>
        ))}
      </div>

      {witnesses.length > 0 && (
        <>
          <h3>Témoins</h3>
          <p className="muted">{witnesses.map((person) => person.name).join(", ")}</p>
        </>
      )}

      {incident.policeVehicle && (
        <button className="entity-link police-link" onClick={() => onSelectVehicle(incident.policeVehicle!.id)}>
          Voir l’unité de police #{incident.policeVehicle.id}
        </button>
      )}
      {incident.policeOfficers.length > 0 && (
        <>
          <h3>Agents intervenants</h3>
          <div className="passenger-list">
            {incident.policeOfficers.filter((person): person is { id: number; name: string } => person !== null).map((person) => (
              <button key={person.id} onClick={() => onSelectCitizen(person.id)}>{person.name}</button>
            ))}
          </div>
        </>
      )}
      {incident.policeAction && <p className="decision"><strong>Mesure immédiate :</strong> {incident.policeAction}</p>}
      {incident.detained.length > 0 && (
        <div className="passenger-list">
          {incident.detained.filter((person): person is { id: number; name: string } => person !== null).map((person) => (
            <button key={person.id} onClick={() => onSelectCitizen(person.id)}>Personne retenue : {person.name}</button>
          ))}
        </div>
      )}

      {incident.investigation && (
        <>
          <h3>Enquête #{incident.investigation.id}</h3>
          <dl className="facts">
            <div><dt>Statut</dt><dd>{incident.investigation.status}</dd></div>
            <div><dt>Confiance</dt><dd>{Math.round(incident.investigation.confidence)} %</dd></div>
            <div><dt>Éléments</dt><dd>{incident.investigation.evidence.length}</dd></div>
          </dl>
          {incident.investigation.leadSuspect && (
            <button className="entity-link danger-link" onClick={() => onSelectCitizen(incident.investigation!.leadSuspect!.id)}>
              Suspect principal : {incident.investigation.leadSuspect.name}
            </button>
          )}
          {incident.investigation.evidence.length > 0 && (
            <>
              <h3>Éléments recueillis</h3>
              <div className="evidence-list">
                {incident.investigation.evidence.map((item) => (
                  <article key={item.id}>
                    <div><strong>{item.type.replace(/_/g, " ")}</strong><b>{Math.round(item.reliability)} %</b></div>
                    <p>{item.description}</p>
                    {item.citizen && (
                      <button onClick={() => onSelectCitizen(item.citizen!.id)}>{item.citizen.name}</button>
                    )}
                  </article>
                ))}
              </div>
            </>
          )}
          {incident.investigation.notes.length > 0 && (
            <>
              <h3>Notes d’enquête</h3>
              <ul className="investigation-notes">
                {incident.investigation.notes.map((note, index) => <li key={`${index}-${note}`}>{note}</li>)}
              </ul>
            </>
          )}
          {incident.investigation.case && (
            <div className="case-summary">
              <h3>Dossier judiciaire #{incident.investigation.case.id}</h3>
              <dl className="facts">
                <div><dt>Statut</dt><dd>{incident.investigation.case.status}</dd></div>
                <div><dt>Charges</dt><dd>{incident.investigation.case.charges.join(", ")}</dd></div>
                <div><dt>Solidité</dt><dd>{Math.round(incident.investigation.case.evidenceScore)} %</dd></div>
                {incident.investigation.case.verdict && <div><dt>Verdict</dt><dd>{incident.investigation.case.verdict}</dd></div>}
                {incident.investigation.case.sentence && <div><dt>Peine</dt><dd>{incident.investigation.case.sentence}</dd></div>}
              </dl>
            </div>
          )}
        </>
      )}

      {incident.resolution && (
        <>
          <h3>Résolution</h3>
          <p className="decision">{incident.resolution}</p>
        </>
      )}
    </div>
  );
}

