import type { VehicleDetail } from "../../types/city";
const VEHICLE_STATUS_LABELS: Record<string, string> = {parked:"Stationné",driving:"En circulation",in_service:"En service",stopped:"Hors service",responding:"En intervention",on_scene:"Sur place",returning:"Retour à la base",transporting:"Transport vers l’hôpital"};
export function VehicleInspector({
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
      : vehicle.type === "ambulance" ? `Ambulance #${vehicle.id}` : `Voiture #${vehicle.id}`;
  return (
    <div className="inspector-content">
      <div className="eyebrow">Véhicule</div>
      <h2>{title}</h2>
      <p className="subtitle">
        {vehicle.type === "bus"
          ? vehicle.line?.name ?? "Transport public"
          : vehicle.type === "police" ? "Patrouille municipale" : vehicle.type === "ambulance" ? "Secours médical" : "Véhicule particulier"}
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

      {(vehicle.type === "police" || vehicle.type === "ambulance") && (
        <>
          <h3>{vehicle.type === "ambulance" ? "Équipage soignant citoyen" : "Équipage citoyen"}</h3>
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

      <h3>{vehicle.type === "police" ? "Personnes transportées" : vehicle.type === "ambulance" ? "Patient transporté" : "Passagers"}</h3>
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

