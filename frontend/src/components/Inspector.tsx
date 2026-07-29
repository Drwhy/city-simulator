import { IncidentInspector } from "./inspectors/IncidentInspector";
import { VehicleInspector } from "./inspectors/VehicleInspector";
import { BuildingInspector } from "./inspectors/BuildingInspector";
import { moneyFormatter, NeedBar } from "./inspectors/shared";
import type { CitizenDetail, InspectorEntity } from "../types/city";

interface InspectorProps {
  entity: InspectorEntity | null;
  loading: boolean;
  refreshing: boolean;
  paused?: boolean;
  onSelectCitizen: (citizenId: number) => void;
  onSelectVehicle: (vehicleId: number) => void;
  onSelectIncident: (incidentId: number) => void;
  onSelectHousehold: (householdId: number) => void;
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
  waiting_medical: "Attend une consultation",
  in_treatment: "En consultation",
  hospitalized: "Hospitalisé",
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

export function Inspector({
  entity,
  loading,
  refreshing,
  onSelectCitizen,
  onSelectVehicle,
  onSelectIncident,
  onSelectHousehold,
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
        <BuildingInspector building={entity} onSelectCitizen={onSelectCitizen} onSelectHousehold={onSelectHousehold} />
      )}
    </aside>
  );
}
