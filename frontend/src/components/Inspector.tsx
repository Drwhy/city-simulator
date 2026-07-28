import type { BuildingDetail, CitizenDetail, IncidentDetail, InspectorEntity, VehicleDetail } from "../types/city";

interface InspectorProps {
  entity: InspectorEntity | null;
  loading: boolean;
  refreshing: boolean;
  paused?: boolean;
  onSelectCitizen: (citizenId: number) => void;
  onSelectVehicle: (vehicleId: number) => void;
  onSelectIncident: (incidentId: number) => void;
  standalone?: boolean;
}

const ACTIVITY_LABELS: Record<string, string> = {
  sleeping: "Dort",
  working: "Travaille",
  walking: "Marche",
  driving: "Conduit",
  waiting_bus: "Attend le bus",
  riding_bus: "Dans le bus",
  eating: "Mange",
  relaxing: "Se détend",
  at_home: "À domicile",
  detained: "Retenu au commissariat",
  shopping: "Fait des courses",
};

const MODE_LABELS: Record<string, string> = {
  walk: "Marche",
  car: "Voiture",
  bus: "Bus",
};

const STAGE_LABELS: Record<string, string> = {
  idle: "Aucun trajet",
  walking: "Marche vers la destination",
  to_bus_stop: "Marche vers l’arrêt",
  waiting_bus: "Attend à l’arrêt",
  on_bus: "À bord du bus",
  from_bus_stop: "Marche depuis l’arrêt",
  driving: "Trajet en voiture",
};

const VEHICLE_STATUS_LABELS: Record<string, string> = {
  parked: "Stationné",
  driving: "En circulation",
  in_service: "En service",
  stopped: "Hors service",
  responding: "En intervention",
  on_scene: "Sur place",
  returning: "Retour au commissariat",
};

const RELATIONSHIP_LABELS: Record<string, string> = {
  unknown: "Inconnu",
  acquaintance: "Connaissance",
  friend: "Ami",
  close_friend: "Ami proche",
  rival: "Rival",
};

const SOCIAL_EVENT_LABELS: Record<string, string> = {
  coffee: "Sortie au café",
  park_meetup: "Rencontre au parc",
};

const moneyFormatter = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

const BUSINESS_STATUS_LABELS: Record<string, string> = {
  healthy: "Saine",
  fragile: "Fragile",
  deficit: "Déficitaire",
  closed: "Fermée",
};

function NeedBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="need-row">
      <div className="need-label">
        <span>{label}</span>
        <strong>{Math.round(value)} %</strong>
      </div>
      <div className="progress">
        <div className="progress-value" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

function CitizenInspector({
  citizen,
  onSelectCitizen,
  onSelectVehicle,
}: {
  citizen: CitizenDetail;
  onSelectCitizen: (citizenId: number) => void;
  onSelectVehicle: (vehicleId: number) => void;
}) {
  return (
    <div className="inspector-content">
      <div className="eyebrow">Habitant #{citizen.id}</div>
      <h2>{citizen.name}</h2>
      <p className="subtitle">{citizen.age} ans · {citizen.jobTitle ?? "Sans emploi"}</p>

      <dl className="facts">
        <div><dt>Activité</dt><dd>{ACTIVITY_LABELS[citizen.activity] ?? citizen.activity}</dd></div>
        <div><dt>Destination</dt><dd>{citizen.destination?.name ?? "Aucune"}</dd></div>
        <div><dt>Domicile</dt><dd>{citizen.home.name}</dd></div>
        <div><dt>Travail</dt><dd>{citizen.workplace?.name ?? "Aucun"}</dd></div>
        <div><dt>Argent</dt><dd>{moneyFormatter.format(citizen.money)}</dd></div>
        <div><dt>Salaire</dt><dd>{moneyFormatter.format(citizen.salaryDaily)}/jour</dd></div>
      </dl>

      <h3>État et historique</h3>
      <NeedBar label="Santé" value={citizen.health} />
      <dl className="facts">
        <div><dt>Infractions</dt><dd>{citizen.criminality.offensesCommitted}</dd></div>
        <div><dt>Victimisations</dt><dd>{citizen.criminality.victimizations}</dd></div>
        <div><dt>Interpellations</dt><dd>{citizen.criminality.arrests}</dd></div>
      </dl>

      <h3>Profil social</h3>
      <dl className="facts">
        <div><dt>Sociabilité</dt><dd>{citizen.personality.sociability.toFixed(0)} %</dd></div>
        <div><dt>Amabilité</dt><dd>{citizen.personality.agreeableness.toFixed(0)} %</dd></div>
        <div><dt>Spontanéité</dt><dd>{citizen.personality.spontaneity.toFixed(0)} %</dd></div>
        <div><dt>Interactions aujourd’hui</dt><dd>{citizen.social.interactionsToday}</dd></div>
      </dl>

      {citizen.household && (
        <>
          <h3>Foyer</h3>
          <div className="household-card">
            <div><span>Cohésion</span><strong>{citizen.household.cohesion.toFixed(0)} %</strong></div>
            <div><span>Repas partagés</span><strong>{citizen.household.sharedMeals}</strong></div>
            <div className="household-members">
              {citizen.household.members.map((member) => (
                <button key={member.id} onClick={() => onSelectCitizen(member.id)}>{member.name}</button>
              ))}
            </div>
          </div>
        </>
      )}

      {citizen.social.event && (
        <>
          <h3>Prochaine rencontre</h3>
          <div className="social-plan">
            <strong>{SOCIAL_EVENT_LABELS[citizen.social.event.type] ?? citizen.social.event.type}</strong>
            <span>{citizen.social.event.building.name}</span>
            <small>{citizen.social.event.status === "active" ? "En cours" : `Dans ${citizen.social.event.minutesUntilStart} min`}</small>
          </div>
        </>
      )}

      <h3>Mobilité</h3>
      <dl className="facts">
        <div><dt>Mode actuel</dt><dd>{MODE_LABELS[citizen.transport.mode]}</dd></div>
        <div><dt>Étape</dt><dd>{STAGE_LABELS[citizen.transport.stage]}</dd></div>
        <div><dt>Dernier trajet</dt><dd>{citizen.transport.lastTripMinutes} min</dd></div>
        <div><dt>Temps aujourd’hui</dt><dd>{citizen.transport.travelMinutesToday} min</dd></div>
        <div><dt>Trajets aujourd’hui</dt><dd>{citizen.transport.tripsToday}</dd></div>
      </dl>

      {(citizen.transport.originStop || citizen.transport.destinationStop) && (
        <p className="transport-route">
          {citizen.transport.originStop?.name ?? "—"}
          <span aria-hidden="true">→</span>
          {citizen.transport.destinationStop?.name ?? "—"}
        </p>
      )}

      {citizen.transport.ownedVehicle && (
        <button
          className="entity-link"
          onClick={() => onSelectVehicle(citizen.transport.ownedVehicle!.id)}
        >
          Voir sa voiture #{citizen.transport.ownedVehicle.id}
        </button>
      )}
      {citizen.transport.activeVehicle
        && citizen.transport.activeVehicle.id !== citizen.transport.ownedVehicle?.id && (
        <button
          className="entity-link"
          onClick={() => onSelectVehicle(citizen.transport.activeVehicle!.id)}
        >
          Voir le véhicule actuel #{citizen.transport.activeVehicle.id}
        </button>
      )}

      <h3>Besoins</h3>
      <NeedBar label="Faim" value={citizen.needs.hunger} />
      <NeedBar label="Fatigue" value={citizen.needs.fatigue} />
      <NeedBar label="Stress" value={citizen.needs.stress} />
      <NeedBar label="Sociabilité" value={citizen.needs.social} />

      <h3>Décision</h3>
      <p className="decision">{citizen.decisionReason}</p>

      <h3>Relations principales</h3>
      {citizen.relationships.length === 0 ? (
        <p className="muted">Aucune relation significative pour le moment.</p>
      ) : (
        <div className="relationship-list">
          {citizen.relationships.slice(0, 6).map((relationship) => (
            <button
              className={`relationship relationship-${relationship.status}`}
              key={relationship.citizenId}
              onClick={() => onSelectCitizen(relationship.citizenId)}
            >
              <strong>{relationship.name}</strong>
              <span>{RELATIONSHIP_LABELS[relationship.status]} · Affection {relationship.affection.toFixed(0)} · Confiance {relationship.trust.toFixed(0)}</span>
              {relationship.conflictLevel > 0 && (
                <small className="conflict-level">Conflit : {relationship.conflictLabel.split("_").join(" ")} · série négative {relationship.consecutiveNegativeInteractions}</small>
              )}
            </button>
          ))}
        </div>
      )}

      <h3>Lieux favoris</h3>
      {citizen.social.favoritePlaces.length === 0 ? (
        <p className="muted">Les habitudes ne sont pas encore assez établies.</p>
      ) : (
        <div className="favorite-places">
          {citizen.social.favoritePlaces.map((place) => (
            <div key={place.id}><span>{place.name}</span><strong>{place.visits} visites</strong></div>
          ))}
        </div>
      )}
    </div>
  );
}

function VehicleInspector({
  vehicle,
  onSelectCitizen,
  onSelectIncident,
}: {
  vehicle: VehicleDetail;
  onSelectCitizen: (citizenId: number) => void;
  onSelectIncident: (incidentId: number) => void;
}) {
  const title = vehicle.type === "bus"
    ? `Bus #${vehicle.id}`
    : vehicle.type === "police"
      ? `Unité de police #${vehicle.id}`
      : `Voiture #${vehicle.id}`;
  return (
    <div className="inspector-content">
      <div className="eyebrow">Véhicule</div>
      <h2>{title}</h2>
      <p className="subtitle">
        {vehicle.type === "bus"
          ? vehicle.line?.name ?? "Transport public"
          : vehicle.type === "police" ? "Patrouille municipale" : "Véhicule particulier"}
      </p>

      <dl className="facts">
        <div><dt>État</dt><dd>{VEHICLE_STATUS_LABELS[vehicle.status] ?? vehicle.status}</dd></div>
        <div><dt>Occupation</dt><dd>{vehicle.occupancy} / {vehicle.capacity}</dd></div>
        <div><dt>Destination</dt><dd>{vehicle.target?.name ?? "Circuit régulier"}</dd></div>
        <div><dt>Retard cumulé</dt><dd>{vehicle.delayMinutes} min</dd></div>
        <div><dt>Distance du jour</dt><dd>{vehicle.distanceToday} cases</dd></div>
        <div><dt>Progression</dt><dd>{vehicle.routeProgress.toFixed(0)} %</dd></div>
      </dl>

      {vehicle.incident && (
        <button className="entity-link incident-link" onClick={() => onSelectIncident(vehicle.incident!.id)}>
          Intervention : {vehicle.incident.title}
        </button>
      )}

      {vehicle.owner && (
        <button className="entity-link" onClick={() => onSelectCitizen(vehicle.owner!.id)}>
          Propriétaire : {vehicle.owner.name}
        </button>
      )}

      {vehicle.type === "police" && (
        <>
          <h3>Équipage citoyen</h3>
          {vehicle.crew.length === 0 ? <p className="muted">Aucun agent affecté : l'unité ne peut pas intervenir.</p> : (
            <div className="passenger-list">
              {vehicle.crew.map((officer) => (
                <button key={officer.id} onClick={() => onSelectCitizen(officer.id)}>
                  {officer.name} · {officer.onDuty ? "en service" : "hors service"}
                </button>
              ))}
            </div>
          )}
        </>
      )}

      <h3>{vehicle.type === "police" ? "Personnes transportées" : "Passagers"}</h3>
      {vehicle.passengers.length === 0 ? (
        <p className="muted">Aucun passager actuellement.</p>
      ) : (
        <div className="passenger-list">
          {vehicle.passengers.map((passenger) => (
            <button key={passenger.id} onClick={() => onSelectCitizen(passenger.id)}>
              {passenger.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function IncidentInspector({
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

function BuildingInspector({
  building,
  onSelectCitizen,
}: {
  building: BuildingDetail;
  onSelectCitizen: (citizenId: number) => void;
}) {
  const isEmployer = building.finance.employeeCapacity > 0;
  const resultClass = building.finance.resultToday >= 0 ? "finance-positive" : "finance-negative";

  return (
    <div className="inspector-content building-inspector">
      <div className="eyebrow">Bâtiment #{building.id}</div>
      <h2>{building.name}</h2>
      {isEmployer && (
        <p className={`business-status business-status-${building.finance.status}`}>
          Entreprise {BUSINESS_STATUS_LABELS[building.finance.status] ?? building.finance.status}
        </p>
      )}
      <p className={`service-status ${building.services.operational ? "operational" : "degraded"}`}>
        {building.services.operational ? "Service opérationnel" : "Service dégradé : personnel insuffisant"}
      </p>
      <dl className="facts">
        <div><dt>Occupation</dt><dd>{building.occupancy} / {building.capacity}</dd></div>
        <div><dt>Personnel présent</dt><dd>{building.services.staffOnDuty} / {building.services.employeesRequired}</dd></div>
        <div><dt>Recettes du jour</dt><dd>{moneyFormatter.format(building.services.revenueToday)}</dd></div>
        {building.type === "shop" && <div><dt>Stock nourriture</dt><dd>{building.services.foodStock.toFixed(0)} unités</dd></div>}
        {building.type === "shop" && <div><dt>Stock biens courants</dt><dd>{building.services.goodsStock.toFixed(0)} unités</dd></div>}
      </dl>
      {isEmployer && <>
        <h3>Économie de l’établissement</h3>
        <dl className="facts business-financial-grid">
          <div><dt>Trésorerie</dt><dd>{moneyFormatter.format(building.finance.cash)}</dd></div>
          <div><dt>Recettes cumulées</dt><dd>{moneyFormatter.format(building.finance.totalRevenue)}</dd></div>
          <div><dt>Masse salariale du jour</dt><dd>{moneyFormatter.format(building.finance.payrollToday)}</dd></div>
          <div><dt>Coûts fixes du jour</dt><dd>{moneyFormatter.format(building.finance.fixedCostsToday)}</dd></div>
          <div className={resultClass}><dt>Résultat du jour</dt><dd>{moneyFormatter.format(building.finance.resultToday)}</dd></div>
          <div><dt>Postes</dt><dd>{building.employees.length} / {building.finance.employeeCapacity}</dd></div>
          <div><dt>Effectif cible</dt><dd>{building.finance.targetEmployees}</dd></div>
          <div><dt>Postes ouverts</dt><dd>{building.finance.openPositions}</dd></div>
        </dl>
        <NeedBar label="Niveau de service" value={building.finance.serviceLevel} />
        <h3>Historique financier</h3>
        {building.finance.financialHistory.length === 0 ? <p className="muted">Le premier bilan sera clôturé en fin de journée.</p> : (
          <div className="financial-history">
            {[...building.finance.financialHistory].reverse().slice(0, 10).map((record) => (
              <article className="financial-history-row" key={record.day}>
                <strong>Jour {record.day}</strong>
                <span>Recettes {moneyFormatter.format(record.revenue)}</span>
                <span>Salaires {moneyFormatter.format(record.payroll)}</span>
                <span>Fixes {moneyFormatter.format(record.fixedCosts)}</span>
                <b className={record.result >= 0 ? "finance-positive" : "finance-negative"}>{moneyFormatter.format(record.result)}</b>
              </article>
            ))}
          </div>
        )}
        <h3>Mouvements de personnel</h3>
        {building.finance.employmentHistory.length === 0 ? <p className="muted">Aucun recrutement, départ ou licenciement enregistré.</p> : (
          <div className="economy-history">
            {[...building.finance.employmentHistory].reverse().slice(0, 12).map((record, index) => (
              <article className={`economy-card employment-${record.eventType}`} key={`${record.tick}-${record.eventType}-${index}`}>
                <div><strong>{record.label}</strong><span>{record.jobTitle ?? "Sans fonction"}</span></div>
                <div><b>{moneyFormatter.format(record.salaryDaily)} / jour</b><span>{record.reason}</span></div>
                <small>Tick {record.tick}</small>
              </article>
            ))}
          </div>
        )}
      </>}
      <h3>Employés</h3>
      {building.employees.length === 0 ? <p className="muted">Aucun employé affecté.</p> : (
        <div className="employee-list">
          {building.employees.map((employee) => (
            <button key={employee.id} onClick={() => onSelectCitizen(employee.id)}>
              <span><strong>{employee.name}</strong><small>{employee.jobTitle ?? "Sans fonction"} · {employee.shift} · perf. {Math.round(employee.performance)} % · sat. {Math.round(employee.satisfaction)} %</small></span>
              <b className={employee.onDuty ? "on-duty" : "off-duty"}>{employee.onDuty ? "En service" : "Hors service"}</b>
            </button>
          ))}
        </div>
      )}
      <h3>Occupants</h3>
      <div className="passenger-list">
        {building.occupants.map((person) => <button key={person.id} onClick={() => onSelectCitizen(person.id)}>{person.name}</button>)}
      </div>
    </div>
  );
}

export function Inspector({
  entity,
  loading,
  refreshing,
  onSelectCitizen,
  onSelectVehicle,
  onSelectIncident,
  standalone = false,
  paused = false,
}: InspectorProps) {
  return (
    <aside className={`panel inspector${standalone ? " inspector-standalone" : ""}`} aria-busy={loading || refreshing}>
      <div className="inspector-header">
        <h2>Inspecteur</h2>
        {entity && (
          <span className={`live-status${refreshing ? " refreshing" : ""}${paused ? " paused" : ""}`}>
            <i aria-hidden="true" />
            {paused ? "En pause" : "En direct"}
          </span>
        )}
      </div>

      {loading && !entity ? (
        <div className="inspector-skeleton" aria-label="Chargement de l’entité">
          <div className="skeleton-line skeleton-short" />
          <div className="skeleton-line skeleton-title" />
          <div className="skeleton-line" />
          <div className="skeleton-block" />
          <div className="skeleton-block" />
        </div>
      ) : !entity ? (
        <p className="muted">Sélectionnez un habitant, un véhicule ou un incident sur la carte.</p>
      ) : entity.kind === "citizen" ? (
        <CitizenInspector
          citizen={entity}
          onSelectCitizen={onSelectCitizen}
          onSelectVehicle={onSelectVehicle}
        />
      ) : entity.kind === "vehicle" ? (
        <VehicleInspector
          vehicle={entity}
          onSelectCitizen={onSelectCitizen}
          onSelectIncident={onSelectIncident}
        />
      ) : entity.kind === "incident" ? (
        <IncidentInspector
          incident={entity}
          onSelectCitizen={onSelectCitizen}
          onSelectVehicle={onSelectVehicle}
        />
      ) : (
        <BuildingInspector building={entity} onSelectCitizen={onSelectCitizen} />
      )}
    </aside>
  );
}
