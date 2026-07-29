import type { BuildingDetail } from "../../types/city";
import { moneyFormatter } from "./shared";

interface BuildingHousingSectionProps {
  housing: NonNullable<BuildingDetail["housing"]>;
  onSelectHousehold: (householdId: number) => void;
}

export function BuildingHousingSection({ housing, onSelectHousehold }: BuildingHousingSectionProps) {
  return (
    <>
      <h3>Monitoring du logement</h3>
      <dl className="facts">
        <div><dt>Résidents / capacité</dt><dd>{housing.residentCount} / {housing.capacity}</dd></div>
        <div><dt>Loyer mensuel</dt><dd>{moneyFormatter.format(housing.rentMonthly)}</dd></div>
        <div><dt>Confort</dt><dd>{housing.comfort.toFixed(0)} %</dd></div>
        <div><dt>État</dt><dd>{housing.condition.toFixed(0)} %</dd></div>
        <div><dt>Propriétaire</dt><dd>{housing.ownerType === "municipal" ? "Municipal" : "Privé"}</dd></div>
        <div><dt>Impayés</dt><dd>{moneyFormatter.format(housing.arrears)}</dd></div>
      </dl>
      <h3>Foyers résidents</h3>
      <div className="passenger-list">
        {housing.households.map((household) => (
          <button key={household.id} onClick={() => onSelectHousehold(household.id)}>
            Foyer #{household.id} · {household.members} membre(s) · {household.status}
          </button>
        ))}
      </div>
      <h3>Historique résidentiel</h3>
      {housing.history.length === 0 ? (
        <p className="muted">Aucun mouvement enregistré.</p>
      ) : (
        <div className="economy-history">
          {housing.history.map((record, index) => (
            <article className="economy-card" key={`${record.tick}-${index}`}>
              <strong>{record.label}</strong><span>{record.reason}</span><small>Tick {record.tick}</small>
            </article>
          ))}
        </div>
      )}
    </>
  );
}