import { useEffect, useState } from "react";
import { getHousehold } from "../api";
import type { HouseholdDetail } from "../types/city";

interface HouseholdModalProps {
  householdId: number | null;
  paused: boolean;
  snapshotTick: number;
  onClose: () => void;
  onSelectCitizen: (id: number) => void;
}

const euro = new Intl.NumberFormat("fr-FR", {
  style: "currency", currency: "EUR", maximumFractionDigits: 0,
});
const STATUS: Record<string, string> = {
  stable: "Stable", searching: "En recherche", temporary: "Hébergement temporaire",
};

export function HouseholdModal({ householdId, paused, snapshotTick, onClose, onSelectCitizen }: HouseholdModalProps) {
  const [data, setData] = useState<HouseholdDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (householdId === null) { setData(null); return; }
    let live = true;
    setLoading(true);
    getHousehold(householdId)
      .then((row) => { if (live) setData(row); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [householdId, paused ? 0 : snapshotTick]);

  if (householdId === null) return null;
  return (
    <div className="entity-modal-overlay" role="dialog" aria-modal="true" onMouseDown={onClose}>
      <section className="entity-modal-window" onMouseDown={(event) => event.stopPropagation()}>
        <button className="entity-modal-close" onClick={onClose}>Fermer</button>
        <div className="inspector-content">
          <div className="eyebrow">Foyer #{householdId}</div>
          <h2>Foyer de {data?.home.name ?? "…"}</h2>
          {loading && !data ? <p>Chargement…</p> : data && (
            <HouseholdContent data={data} onSelectCitizen={onSelectCitizen} />
          )}
        </div>
      </section>
    </div>
  );
}

function HouseholdContent({ data, onSelectCitizen }: {
  data: HouseholdDetail;
  onSelectCitizen: (id: number) => void;
}) {
  return (
    <>
      <p className={`business-status business-status-${data.status}`}>
        {STATUS[data.status] ?? data.status}{data.searchReason ? ` · ${data.searchReason}` : ""}
      </p>
      <h3>Budget commun et logement</h3>
      <dl className="facts">
        <div><dt>Membres</dt><dd>{data.members}</dd></div>
        <div><dt>Revenu mensuel estimé</dt><dd>{euro.format(data.incomeMonthly)}</dd></div>
        <div><dt>Réserves communes</dt><dd>{euro.format(data.commonBudget)}</dd></div>
        <div><dt>Loyer mensuel</dt><dd>{euro.format(data.rentMonthly)}</dd></div>
        <div><dt>Impayés</dt><dd>{euro.format(data.rentArrears)}</dd></div>
        <div><dt>Cohésion</dt><dd>{data.cohesion.toFixed(0)} %</dd></div>
        <div><dt>Confort</dt><dd>{data.home.comfort.toFixed(0)} %</dd></div>
        <div><dt>Distance travail moyenne</dt><dd>{data.commuteDistance} cases</dd></div>
      </dl>
      <h3>Dépenses du jour</h3>
      <dl className="facts">
        <div><dt>Loyer payé</dt><dd>{euro.format(data.expenses.rentPaidToday)} / {euro.format(data.expenses.rentDueToday)}</dd></div>
        <div><dt>Charges</dt><dd>{euro.format(data.expenses.recurringToday)}</dd></div>
        <div><dt>Alimentation</dt><dd>{euro.format(data.expenses.foodToday)}</dd></div>
        <div><dt>Biens</dt><dd>{euro.format(data.expenses.goodsToday)}</dd></div>
      </dl>
      <h3>Membres</h3>
      <div className="passenger-list">
        {data.membersList.filter((person): person is { id: number; name: string } => person !== null).map((person) => (
          <button key={person.id} onClick={() => onSelectCitizen(person.id)}>{person.name}</button>
        ))}
      </div>
      <h3>Historique résidentiel</h3>
      {data.housingHistory.length === 0 ? <p className="muted">Aucun déménagement enregistré.</p> : (
        <div className="economy-history">
          {data.housingHistory.map((record, index) => (
            <article className="economy-card" key={`${record.tick}-${index}`}>
              <strong>{record.label}</strong><span>{record.reason}</span>
              <small>Loyer {euro.format(record.rentBefore)} → {euro.format(record.rentAfter)} · tick {record.tick}</small>
            </article>
          ))}
        </div>
      )}
    </>
  );
}