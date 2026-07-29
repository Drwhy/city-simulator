import { useMemo, useState } from "react";
import type { CrimeOverview } from "../types/city";
import "./CrimeMonitoring.css";

type CrimeTab = "factions" | "markets" | "transactions" | "territories" | "operations";

const FACTION_LABELS: Record<string, string> = {
  street_gang: "Gang de rue",
  organized_gang: "Gang organisé",
  mafia: "Mafia",
  triad: "Triade",
  cartel: "Cartel",
  biker_gang: "Gang de motards",
  cyber_network: "Réseau cybercriminel",
};

const COMMODITY_LABELS: Record<string, string> = {
  cannabis: "Cannabis",
  cocaine: "Cocaïne",
  synthetic_drugs: "Drogues de synthèse",
  stolen_goods: "Biens volés",
  weapons: "Armes",
  counterfeit_goods: "Contrefaçons",
};

function label(value: string, labels: Record<string, string>) {
  return labels[value] ?? value.replace(/_/g, " ");
}

export function CrimeMonitoring({
  open,
  data,
  onClose,
  onSelectCitizen,
  onSelectIncident,
  onSelectNeighborhood,
}: {
  open: boolean;
  data: CrimeOverview | null;
  onClose: () => void;
  onSelectCitizen: (id: number) => void;
  onSelectIncident: (id: number) => void;
  onSelectNeighborhood: (id: number) => void;
}) {
  const [tab, setTab] = useState<CrimeTab>("factions");
  const factions = useMemo(
    () => data?.organizations.slice().sort((a, b) => b.policeHeat - a.policeHeat) ?? [],
    [data],
  );
  if (!open) return null;
  const metrics = data?.metrics;

  return (
    <div className="graph-overlay" role="dialog" aria-modal="true" aria-label="Monitoring criminel" onMouseDown={onClose}>
      <section className="crime-monitor" onMouseDown={(event) => event.stopPropagation()}>
        <header className="crime-header">
          <div>
            <div className="eyebrow">Renseignement · marchés clandestins · territoires</div>
            <h2>Activités criminelles</h2>
            <p>Les transactions non détectées figurent comme renseignement de simulation, pas comme connaissance policière.</p>
          </div>
          <button onClick={onClose}>Fermer</button>
        </header>

        <div className="crime-kpis">
          <span><b>{metrics?.organizations ?? 0}</b> factions</span>
          <span><b>{metrics?.factionMembers ?? 0}</b> membres</span>
          <span><b>{metrics?.illegalSalesToday ?? 0}</b> ventes aujourd’hui</span>
          <span><b>{Math.round(metrics?.illegalRevenueToday ?? 0)} €</b> de flux</span>
          <span><b>{metrics?.dependentCitizens ?? 0}</b> dépendances</span>
          <span><b>{metrics?.contestedNeighborhoods ?? 0}</b> territoires disputés</span>
        </div>

        <nav className="crime-tabs" aria-label="Vues du monitoring criminel">
          {([
            ["factions", "Factions"],
            ["markets", "Marchés"],
            ["transactions", "Transactions"],
            ["territories", "Territoires"],
            ["operations", "Opérations"],
          ] as Array<[CrimeTab, string]>).map(([value, title]) => (
            <button className={tab === value ? "active" : ""} key={value} onClick={() => setTab(value)}>{title}</button>
          ))}
        </nav>

        <div className="crime-content">
          {tab === "factions" && (
            <div className="crime-card-grid">
              {factions.map((faction) => (
                <article className="crime-card" key={faction.id}>
                  <header><span className={`crime-type crime-type-${faction.factionType}`}>{label(faction.factionType, FACTION_LABELS)}</span><b>Chaleur {Math.round(faction.policeHeat)} %</b></header>
                  <h3>{faction.name}</h3>
                  <button className="crime-person" onClick={() => onSelectCitizen(faction.leaderId)}>Chef : {faction.leaderName}</button>
                  <dl>
                    <div><dt>Membres</dt><dd>{faction.memberCount}</dd></div>
                    <div><dt>Marchés</dt><dd>{faction.marketCount}</dd></div>
                    <div><dt>Trésorerie</dt><dd>{Math.round(faction.treasury)} €</dd></div>
                    <div><dt>Recettes du jour</dt><dd>{Math.round(faction.revenueToday)} €</dd></div>
                    <div><dt>Violence</dt><dd>{Math.round(faction.violence)} %</dd></div>
                    <div><dt>Sophistication</dt><dd>{Math.round(faction.sophistication)} %</dd></div>
                  </dl>
                  <p>{faction.specialties.map((item) => label(item, COMMODITY_LABELS)).join(" · ")}</p>
                  <button onClick={() => faction.territoryId && onSelectNeighborhood(faction.territoryId)}>Inspecter le territoire principal</button>
                </article>
              ))}
            </div>
          )}

          {tab === "markets" && (
            <div className="crime-table-wrap"><table className="crime-table"><thead><tr><th>Faction</th><th>Produit</th><th>Territoire</th><th>Offre</th><th>Prix</th><th>Demande</th><th>Pression police</th><th>Ventes</th></tr></thead><tbody>
              {data?.markets.map((market) => <tr key={market.id}><td>{market.organizationName}</td><td>{label(market.commodity, COMMODITY_LABELS)}</td><td><button onClick={() => onSelectNeighborhood(market.neighborhoodId)}>{market.neighborhoodName}</button></td><td>{market.supply.toFixed(1)}</td><td>{market.unitPrice.toFixed(0)} €</td><td>{Math.round(market.demand)} %</td><td>{Math.round(market.policePressure)} %</td><td>{market.transactionsToday}</td></tr>)}
            </tbody></table></div>
          )}

          {tab === "transactions" && (
            <div className="crime-feed">
              {data?.transactions.map((transaction) => <article className={transaction.detected ? "detected" : ""} key={transaction.id}><span><b>{label(transaction.commodity, COMMODITY_LABELS)}</b><small>tick {transaction.tick} · {transaction.quantity.toFixed(2)} unité</small></span><span><button onClick={() => onSelectCitizen(transaction.seller.id)}>{transaction.seller.name}</button> → <button onClick={() => onSelectCitizen(transaction.buyer.id)}>{transaction.buyer.name}</button></span><strong>{transaction.total.toFixed(2)} € {transaction.detected ? "· détectée" : "· clandestine"}</strong></article>)}
              {!data?.transactions.length && <p className="muted">Aucune transaction enregistrée.</p>}
            </div>
          )}

          {tab === "territories" && (
            <div className="crime-card-grid">
              {data?.territories.map((territory) => <button className="crime-territory" key={territory.neighborhoodId} onClick={() => onSelectNeighborhood(territory.neighborhoodId)}><span><strong>{territory.neighborhoodName}</strong><small>Contesté à {Math.round(territory.contestedness)} %</small></span><div>{territory.factions.slice(0, 3).filter((row) => row.influence > 0).map((row) => <i key={row.organizationId} style={{ width: `${Math.max(4, row.influence)}%` }} title={`${row.name}: ${row.influence}%`} />)}</div></button>)}
            </div>
          )}

          {tab === "operations" && (
            <div className="crime-feed">
              {data?.operations.map((operation) => <article className={operation.detected ? "detected" : ""} key={operation.id}><span><b>{label(operation.type, {})}</b><small>{operation.organizationName} · {operation.status}</small></span><strong>{operation.amount ? `${Math.round(operation.amount)} €` : operation.outcome ?? "—"}</strong>{operation.incidentId && <button onClick={() => onSelectIncident(operation.incidentId!)}>Incident #{operation.incidentId}</button>}</article>)}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
