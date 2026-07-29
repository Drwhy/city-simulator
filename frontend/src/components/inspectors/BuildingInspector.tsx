import type { BuildingDetail } from "../../types/city";
import { BuildingHousingSection } from "./BuildingHousingSection";
import { BuildingJusticeSection } from "./BuildingJusticeSection";
import { moneyFormatter, NeedBar } from "./shared";
const BUSINESS_STATUS_LABELS: Record<string, string> = {
  healthy: "Saine",
  fragile: "Fragile",
  deficit: "Déficitaire",
  closed: "Fermée",
};
export function BuildingInspector({
  building,
  onSelectCitizen,
  onSelectHousehold,
}: {
  building: BuildingDetail;
  onSelectCitizen: (citizenId: number) => void;
  onSelectHousehold: (householdId: number) => void;
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
      {building.housing && (
        <BuildingHousingSection
          housing={building.housing}
          onSelectHousehold={onSelectHousehold}
        />
      )}
      {building.justice && (
        <BuildingJusticeSection justice={building.justice} onSelectCitizen={onSelectCitizen} />
      )}
      <dl className="facts">
        <div><dt>Occupation</dt><dd>{building.occupancy} / {building.capacity}</dd></div>
        <div><dt>Personnel présent</dt><dd>{building.services.staffOnDuty} / {building.services.employeesRequired}</dd></div>
        <div><dt>Recettes du jour</dt><dd>{moneyFormatter.format(building.services.revenueToday)}</dd></div>
        {building.type === "shop" && <div><dt>Stock nourriture</dt><dd>{building.services.foodStock.toFixed(0)} unités</dd></div>}
        {building.type === "shop" && <div><dt>Stock biens courants</dt><dd>{building.services.goodsStock.toFixed(0)} unités</dd></div>}
      </dl>
      {building.healthcare && <>
        <h3>Monitoring hospitalier</h3>
        <dl className="facts healthcare-grid">
          <div><dt>Lits occupés</dt><dd>{building.healthcare.hospitalized.length} / {building.healthcare.beds}</dd></div>
          <div><dt>File d’attente</dt><dd>{building.healthcare.queue.length}</dd></div>
          <div><dt>Patients traités aujourd’hui</dt><dd>{building.healthcare.patientsTreatedToday}</dd></div>
          <div><dt>Ambulances suivies</dt><dd>{building.healthcare.ambulances.length}</dd></div>
        </dl>
        <h3>File de consultation</h3>
        <div className="passenger-list">{building.healthcare.queue.map((item) => <button key={item.id} onClick={() => onSelectCitizen(item.citizen.id)}>{item.citizen.name} · gravité {Math.round(item.severity)} % · {item.waitingMinutes} min</button>)}</div>
        <h3>Patients hospitalisés</h3>
        <div className="passenger-list">{building.healthcare.hospitalized.filter((person): person is { id: number; name: string } => person !== null).map((person) => <button key={person.id} onClick={() => onSelectCitizen(person.id)}>{person.name}</button>)}</div>
      </>}
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

