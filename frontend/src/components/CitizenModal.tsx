import { useEffect, useMemo, useState } from "react";
import type { MouseEvent } from "react";
import { getCitizen } from "../api";
import { CommunicationPanel } from "./CommunicationPanel";
import type { CitizenDetail, ConflictHistoryEntry, JudicialCaseSummary } from "../types/city";

type CitizenTab = "overview" | "health" | "work" | "social" | "communications" | "conflicts" | "justice";

interface CitizenModalProps {
  citizenId: number | null;
  graphContext?: boolean;
  paused: boolean;
  snapshotTick: number;
  onClose: () => void;
  onData?: (citizen: CitizenDetail) => void;
  onSelectCitizen: (citizenId: number) => void;
  onSelectIncident: (incidentId: number) => void;
  onSelectCase: (caseId: number) => void;
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

const RELATIONSHIP_LABELS: Record<string, string> = {
  unknown: "Inconnu",
  acquaintance: "Connaissance",
  friend: "Ami",
  close_friend: "Ami proche",
  rival: "Rival",
};

const INVESTIGATION_LABELS: Record<string, string> = {
  open: "Enquête ouverte",
  suspect_identified: "Suspect identifié",
  arrested: "Arrestation effectuée",
  referred: "Transmis à la justice",
  closed: "Enquête close",
};

const CASE_LABELS: Record<string, string> = {
  filed: "Dossier déposé",
  awaiting_hearing: "Audience en attente",
  decided: "Jugé",
  dismissed: "Classé / relaxé",
};

const moneyFormatter = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

function MetricBar({ label, value, warning = false }: { label: string; value: number; warning?: boolean }) {
  return (
    <div className="profile-metric">
      <div><span>{label}</span><strong>{Math.round(value)} %</strong></div>
      <div className="profile-meter"><i className={warning ? "warning" : ""} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>
    </div>
  );
}

function TickLabel({ tick, currentTick }: { tick: number; currentTick: number }) {
  const minutesAgo = Math.max(0, currentTick - tick);
  if (minutesAgo < 60) return <>{minutesAgo} min auparavant</>;
  if (minutesAgo < 1440) return <>{Math.floor(minutesAgo / 60)} h auparavant</>;
  return <>{Math.floor(minutesAgo / 1440)} j auparavant</>;
}

function ConflictRow({
  row,
  currentTick,
  onSelectIncident,
}: {
  row: ConflictHistoryEntry;
  currentTick: number;
  onSelectIncident: (incidentId: number) => void;
}) {
  return (
    <article className={`conflict-history-row conflict-history-level-${row.level}`}>
      <div className="conflict-history-heading">
        <div>
          <strong>{row.title}</strong>
          <span>{row.otherName ? `avec ${row.otherName}` : row.role}</span>
        </div>
        <b>Niveau {row.level}</b>
      </div>
      <p>
        <TickLabel tick={row.tick} currentTick={currentTick} />
        {row.buildingName ? ` · ${row.buildingName}` : ""}
        {row.role ? ` · rôle : ${row.role}` : ""}
      </p>
      {row.outcome && <p className="conflict-outcome">{row.outcome}</p>}
      {row.incidentId !== null && (
        <button onClick={() => onSelectIncident(row.incidentId!)}>Ouvrir l’incident #{row.incidentId}</button>
      )}
    </article>
  );
}

function CaseCard({ row, currentTick, onSelectCase }: { row: JudicialCaseSummary; currentTick: number; onSelectCase: (caseId: number) => void }) {
  const untilHearing = row.hearingTick - currentTick;
  return (
    <article className="justice-card">
      <header>
        <strong>Dossier #{row.id}</strong>
        <span>{CASE_LABELS[row.status] ?? row.status}</span>
      </header>
      <p>{row.charges.join(", ")}</p>
      <dl>
        <div><dt>Solidité</dt><dd>{Math.round(row.evidenceScore)} %</dd></div>
        {row.status === "awaiting_hearing" && <div><dt>Audience</dt><dd>dans {Math.max(0, Math.round(untilHearing / 60))} h</dd></div>}
        {row.verdict && <div><dt>Verdict</dt><dd>{row.verdict}</dd></div>}
        {row.sentence && <div><dt>Peine</dt><dd>{row.sentence}</dd></div>}
      </dl>
      <button onClick={() => onSelectCase(row.id)}>Ouvrir le dossier complet</button>
    </article>
  );
}

export function CitizenModal({ citizenId, graphContext = false, paused, snapshotTick, onClose, onData, onSelectCitizen, onSelectIncident, onSelectCase }: CitizenModalProps) {
  const [citizen, setCitizen] = useState<CitizenDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [tab, setTab] = useState<CitizenTab>("overview");

  useEffect(() => {
    if (citizenId === null) {
      setCitizen(null);
      return;
    }
    const initial = citizen?.id !== citizenId;
    if (initial) setCitizen(null);
    let disposed = false;
    let requestInFlight = false;
    const refresh = async (initial: boolean) => {
      if (requestInFlight) return;
      requestInFlight = true;
      if (initial) setLoading(true);
      else setRefreshing(true);
      try {
        const data = await getCitizen(citizenId);
        if (!disposed) {
          setCitizen(data);
          onData?.(data);
        }
      } finally {
        requestInFlight = false;
        if (!disposed) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    };
    void refresh(initial);
    const timer = paused ? null : window.setInterval(() => void refresh(false), 1200);
    return () => {
      disposed = true;
      if (timer !== null) window.clearInterval(timer);
    };
  }, [citizenId, paused, paused ? snapshotTick : 0, onData]);

  useEffect(() => {
    setTab("overview");
  }, [citizenId]);


  const conflictRelations = useMemo(
    () => citizen?.relationships.filter((relationship) => relationship.conflictLevel > 0 || relationship.negativeInteractions > 0) ?? [],
    [citizen],
  );

  if (citizenId === null) return null;

  return (
    <div
      className={`citizen-modal-overlay${graphContext ? " graph-context" : ""}`}
      role="dialog"
      aria-modal={!graphContext}
      aria-label="Fiche habitant"
      onMouseDown={graphContext ? undefined : onClose}
    >
      <section className="citizen-modal" onMouseDown={(event: MouseEvent<HTMLElement>) => event.stopPropagation()}>
        <header className="citizen-modal-header">
          <div>
            <div className="eyebrow">Fiche habitant · #{citizenId}</div>
            <h2>{citizen?.name ?? "Chargement…"}</h2>
            <p>{citizen ? `${citizen.age} ans · ${ACTIVITY_LABELS[citizen.activity] ?? citizen.activity}` : "Récupération des données"}</p>
          </div>
          <div className="citizen-modal-actions">
            {citizen && <span className={`live-status${refreshing ? " refreshing" : ""}${paused ? " paused" : ""}`}><i /> {paused ? "En pause" : "En direct"}</span>}
            <button onClick={onClose}>Fermer</button>
          </div>
        </header>

        <nav className="citizen-tabs" aria-label="Sections de la fiche">
          {([
            ["overview", "Vue générale"],
            ["health", "Santé"],
            ["work", "Travail et finances"],
            ["social", "Réseau social"],
            ["communications", `Communications${citizen?.communications.unreadCount ? ` (${citizen.communications.unreadCount})` : ""}`],
            ["conflicts", `Conflits${citizen ? ` (${citizen.conflictHistory.length})` : ""}`],
            ["justice", "Police & justice"],
          ] as Array<[CitizenTab, string]>).map(([value, label]) => (
            <button className={tab === value ? "active" : ""} key={value} onClick={() => setTab(value)}>{label}</button>
          ))}
        </nav>

        <div className="citizen-modal-body">
          {loading && !citizen ? (
            <div className="profile-loading">Chargement de la fiche…</div>
          ) : !citizen ? (
            <div className="profile-loading">Habitant introuvable.</div>
          ) : tab === "overview" ? (
            <div className="profile-grid">
              <section className="profile-section">
                <h3>Situation</h3>
                <dl className="profile-facts">
                  <div><dt>Domicile</dt><dd>{citizen.home.name}</dd></div>
                  <div><dt>Emploi</dt><dd>{citizen.jobTitle ?? "Sans emploi"}</dd></div>
                  <div><dt>Lieu de travail</dt><dd>{citizen.workplace?.name ?? "—"}</dd></div>
                  <div><dt>Destination</dt><dd>{citizen.destination?.name ?? "—"}</dd></div>
                  <div><dt>Logement</dt><dd>{citizen.housingSituation.isHomeless ? "Sans abri" : "Logé"}</dd></div>
                  <div><dt>Liquide</dt><dd>{moneyFormatter.format(citizen.banking.cash)}</dd></div>
                  <div><dt>Compte bancaire</dt><dd>{moneyFormatter.format(citizen.banking.balance)}</dd></div>
                  <div><dt>Épargne</dt><dd>{moneyFormatter.format(citizen.banking.savings)}</dd></div>
                  <div><dt>Dette bancaire</dt><dd>{moneyFormatter.format(citizen.banking.debt)}</dd></div>
                  <div><dt>Score de crédit</dt><dd>{Math.round(citizen.banking.creditScore)} / 100</dd></div>
                  <div><dt>Santé</dt><dd>{Math.round(citizen.health)} %</dd></div>
                </dl>
                <h3>Décision actuelle</h3>
                <p className="decision">{citizen.decisionReason}</p>
              </section>

              <section className="profile-section">
                <h3>Besoins</h3>
                <MetricBar label="Faim" value={citizen.needs.hunger} warning />
                <MetricBar label="Fatigue" value={citizen.needs.fatigue} warning />
                <MetricBar label="Stress" value={citizen.needs.stress} warning />
                <MetricBar label="Besoin social" value={citizen.needs.social} warning />
              </section>

              <section className="profile-section">
                <h3>Personnalité</h3>
                <div className={`temperament-badge temperament-${citizen.personality.temperament.replace(/ /g, "-")}`}>
                  Tempérament : {citizen.personality.temperament}
                </div>
                <MetricBar label="Sociabilité" value={citizen.personality.sociability} />
                <MetricBar label="Amabilité" value={citizen.personality.agreeableness} />
                <MetricBar label="Agressivité" value={citizen.personality.aggression} warning />
                <MetricBar label="Impulsivité" value={citizen.personality.impulsivity} warning />
                <MetricBar label="Tendance à la rancune" value={citizen.personality.grudgeTendency} warning />
                <MetricBar label="Propension globale au conflit" value={citizen.personality.conflictPropensity} warning />
              </section>
            </div>
          ) : tab === "health" ? (
            <div className="profile-grid profile-grid-health">
              <section className="profile-section">
                <h3>État de santé</h3>
                <MetricBar label="Santé générale" value={citizen.health} />
                <MetricBar label="Douleur" value={citizen.medical.pain} warning />
                <MetricBar label="Blessure" value={citizen.medical.injurySeverity} warning />
                <MetricBar label="Maladie" value={citizen.medical.illnessSeverity} warning />
                <dl className="profile-facts">
                  <div><dt>État</dt><dd>{citizen.medical.condition.replace(/_/g, " ")}</dd></div>
                  <div><dt>Prise en charge</dt><dd>{citizen.medical.careStatus.replace(/_/g, " ")}</dd></div>
                  <div><dt>Dossier actif</dt><dd>{citizen.medical.activeCaseId ? `#${citizen.medical.activeCaseId}` : "Aucun"}</dd></div>
                  <div><dt>Arrêt de travail</dt><dd>{citizen.medical.medicalLeaveUntilTick && citizen.medical.medicalLeaveUntilTick > citizen.currentTick ? `${citizen.medical.medicalLeaveUntilTick - citizen.currentTick} min restantes` : "Non"}</dd></div>
                  <div><dt>Incapacité temporaire</dt><dd>{citizen.medical.incapacityUntilTick && citizen.medical.incapacityUntilTick > citizen.currentTick ? `${citizen.medical.incapacityUntilTick - citizen.currentTick} min restantes` : "Non"}</dd></div>
                </dl>
              </section>
              <section className="profile-section profile-section-wide">
                <h3>Historique médical</h3>
                {citizen.medical.history.length === 0 ? <p className="muted">Aucun épisode médical enregistré.</p> : (
                  <div className="economy-history">
                    {citizen.medical.history.map((record, index) => (
                      <article className="economy-card medical-record" key={`${record.tick}-${index}`}>
                        <div><strong>{record.label}</strong><span>Gravité {Math.round(record.severity)} %</span></div>
                        <p>{record.source}</p>
                        <small><TickLabel tick={record.tick} currentTick={citizen.currentTick} />{record.incapacityMinutes ? ` · incapacité ${record.incapacityMinutes} min` : ""}</small>
                        {record.incidentId !== null && <button onClick={() => onSelectIncident(record.incidentId!)}>Ouvrir l’incident #{record.incidentId}</button>}
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </div>
          ) : tab === "work" ? (
            <div className="profile-grid profile-grid-work">
              <section className="profile-section">
                <h3>Emploi</h3>
                <dl className="profile-facts">
                  <div><dt>Statut</dt><dd>{citizen.employment.status === "employed" ? "Employé" : "Sans emploi"}</dd></div>
                  <div><dt>Fonction</dt><dd>{citizen.jobTitle ?? "—"}</dd></div>
                  <div><dt>Employeur</dt><dd>{citizen.workplace?.name ?? "—"}</dd></div>
                  <div><dt>Horaire</dt><dd>{citizen.employment.workStartHour.toString().padStart(2, "0")}:00–{citizen.employment.workEndHour.toString().padStart(2, "0")}:00</dd></div>
                  <div><dt>En service</dt><dd>{citizen.employment.onDuty ? "Oui" : "Non"}</dd></div>
                  <div><dt>Temps travaillé aujourd’hui</dt><dd>{citizen.employment.minutesWorkedToday} min</dd></div>
                  <div><dt>Shifts terminés</dt><dd>{citizen.employment.shiftsCompleted}</dd></div>
                  <div><dt>Shifts manqués / incomplets</dt><dd>{citizen.employment.missedShifts}</dd></div>
                  <div><dt>Salaire journalier</dt><dd>{moneyFormatter.format(citizen.salaryDaily)}</dd></div>
                  <div><dt>Recherche active</dt><dd>{citizen.employment.jobSearchActive ? "Oui" : "Non"}</dd></div>
                  <div><dt>Dernier changement</dt><dd>{citizen.employment.lastJobChangeTick > 0 ? <TickLabel tick={citizen.employment.lastJobChangeTick} currentTick={citizen.currentTick} /> : "Emploi initial"}</dd></div>
                  <div><dt>Revenus aujourd’hui</dt><dd>{moneyFormatter.format(citizen.employment.incomeToday)}</dd></div>
                  <div><dt>Dépenses aujourd’hui</dt><dd>{moneyFormatter.format(citizen.employment.expensesToday)}</dd></div>
                </dl>
                <MetricBar label="Performance" value={citizen.employment.performance} />
                <MetricBar label="Satisfaction professionnelle" value={citizen.employment.satisfaction} />
                <MetricBar label="Stress financier" value={citizen.employment.financialStress} warning />
              </section>
              <section className="profile-section">
                <h3>Budget et réserves du foyer</h3>
                <dl className="profile-facts">
                  <div><dt>Nourriture</dt><dd>{citizen.consumption.foodUnits.toFixed(1)} unités</dd></div>
                  <div><dt>Biens courants</dt><dd>{citizen.consumption.goodsUnits.toFixed(1)} unités</dd></div>
                  <div><dt>Visites au marché</dt><dd>{citizen.consumption.shoppingVisits}</dd></div>
                  <div><dt>Alcoolémie simulée</dt><dd>{Math.round(citizen.consumption.intoxication)} %</dd></div>
                  {citizen.household && <>
                    <div><dt>Revenus du foyer</dt><dd>{moneyFormatter.format(citizen.household.incomeToday)}</dd></div>
                    <div><dt>Charges récurrentes</dt><dd>{moneyFormatter.format(citizen.household.recurringExpensesToday)}</dd></div>
                    <div><dt>Dépenses alimentaires</dt><dd>{moneyFormatter.format(citizen.household.foodExpensesToday)}</dd></div>
                    <div><dt>Dépenses en biens</dt><dd>{moneyFormatter.format(citizen.household.goodsExpensesToday)}</dd></div>
                    <div><dt>Dette du foyer</dt><dd>{moneyFormatter.format(citizen.household.debt)}</dd></div>
                    <div><dt>Découvert autorisé</dt><dd>{moneyFormatter.format(citizen.household.overdraftLimit)}</dd></div>
                    <div><dt>Budget nourriture</dt><dd>{moneyFormatter.format(citizen.household.budgets.foodDaily)} / jour</dd></div>
                    <div><dt>Budget biens</dt><dd>{moneyFormatter.format(citizen.household.budgets.goodsDaily)} / jour</dd></div>
                  </>}
                </dl>
                {citizen.household && <MetricBar label="Stress financier du foyer" value={citizen.household.financialStress} warning />}
                <p className="muted">Les réserves couvrent volontairement de grandes catégories : alimentation et biens de consommation courante.</p>
              </section>
              <section className="profile-section profile-section-wide">
                <h3>Candidatures</h3>
                {citizen.employment.applications.length === 0 ? <p className="muted">Aucune candidature enregistrée.</p> : (
                  <div className="economy-history">
                    {[...citizen.employment.applications].reverse().map((application) => (
                      <article className={`economy-card application-${application.status}`} key={application.id}>
                        <div><strong>{application.jobTitle}</strong><span>{application.building.name}</span></div>
                        <div><b>{moneyFormatter.format(application.salaryDaily)} / jour</b><span>{application.status}</span></div>
                        <small>
                          Déposée <TickLabel tick={application.submittedTick} currentTick={citizen.currentTick} />
                          {application.reason ? ` · ${application.reason}` : ""}
                        </small>
                      </article>
                    ))}
                  </div>
                )}
              </section>
              <section className="profile-section profile-section-wide">
                <h3>Historique professionnel</h3>
                {citizen.employment.history.length === 0 ? <p className="muted">Emploi initial, aucun changement enregistré.</p> : (
                  <div className="economy-history">
                    {[...citizen.employment.history].reverse().map((record, index) => (
                      <article className={`economy-card employment-${record.eventType}`} key={`${record.tick}-${record.eventType}-${index}`}>
                        <div><strong>{record.label}</strong><span>{record.jobTitle ?? "Sans fonction"}</span></div>
                        <div><b>{moneyFormatter.format(record.salaryDaily)} / jour</b><span>{record.reason}</span></div>
                        <small><TickLabel tick={record.tick} currentTick={citizen.currentTick} /></small>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </div>
          ) : tab === "social" ? (
            <div className="profile-grid profile-grid-social">
              <section className="profile-section">
                <h3>Foyer</h3>
                {citizen.household ? (
                  <>
                    <dl className="profile-facts">
                      <div><dt>Cohésion</dt><dd>{Math.round(citizen.household.cohesion)} %</dd></div>
                      <div><dt>Repas partagés</dt><dd>{citizen.household.sharedMeals}</dd></div>
                      <div><dt>Conflits domestiques</dt><dd>{citizen.household.conflicts}</dd></div>
                    </dl>
                    <div className="profile-links">
                      {citizen.household.members.map((member) => (
                        <button key={member.id} onClick={() => onSelectCitizen(member.id)}>{member.name}</button>
                      ))}
                    </div>
                  </>
                ) : <p className="muted">Aucun foyer renseigné.</p>}
              </section>

              <section className="profile-section profile-section-wide">
                <h3>Relations</h3>
                <div className="profile-relationships">
                  {citizen.relationships.map((relationship) => (
                    <button
                      className={`profile-relationship relationship-${relationship.status}`}
                      key={relationship.citizenId}
                      onClick={() => onSelectCitizen(relationship.citizenId)}
                    >
                      <span><strong>{relationship.name}</strong><small>{RELATIONSHIP_LABELS[relationship.status] ?? relationship.status}</small></span>
                      <span className="relationship-numbers">
                        <b>Aff. {Math.round(relationship.affection)}</b>
                        <b>Conf. {Math.round(relationship.trust)}</b>
                        {relationship.conflictLevel > 0 && <em>Conflit {relationship.conflictLevel}</em>}
                      </span>
                    </button>
                  ))}
                </div>
              </section>
            </div>
          ) : tab === "communications" ? (
            <CommunicationPanel citizen={citizen} onSelectCitizen={onSelectCitizen} />
          ) : tab === "conflicts" ? (
            <div className="conflict-tab-layout">
              <section className="profile-section conflict-summary">
                <h3>État conflictuel</h3>
                <dl className="profile-facts">
                  <div><dt>Différends connus</dt><dd>{conflictRelations.length}</dd></div>
                  <div><dt>Épisodes mémorisés</dt><dd>{citizen.conflictHistory.length}</dd></div>
                  <div><dt>Infractions</dt><dd>{citizen.criminality.offensesCommitted}</dd></div>
                  <div><dt>Victimisations</dt><dd>{citizen.criminality.victimizations}</dd></div>
                </dl>
                <p className="muted">Les échanges positifs peuvent apaiser une relation, mais une personnalité rancunière conserve plus longtemps la pression accumulée.</p>
                <h3>Différends mémorisés</h3>
                {conflictRelations.length === 0 ? (
                  <p className="muted">Aucun différend actif.</p>
                ) : (
                  <div className="conflict-relations-list">
                    {conflictRelations.map((relationship) => (
                      <button key={relationship.citizenId} onClick={() => onSelectCitizen(relationship.citizenId)}>
                        <span>
                          <strong>{relationship.name}</strong>
                          <small>{relationship.conflictLabel} · {relationship.negativeInteractions} interaction(s) négative(s)</small>
                        </span>
                        <span>
                          <b>Niveau {relationship.conflictLevel}</b>
                          <small>Pic {relationship.peakConflictLevel}</small>
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </section>
              <section className="profile-section conflict-timeline">
                <h3>Historique complet</h3>
                {citizen.conflictHistory.length === 0 ? (
                  <p className="muted">Aucun conflit mémorisé.</p>
                ) : citizen.conflictHistory.map((row, index) => (
                  <ConflictRow key={`${row.tick}-${row.incidentId}-${index}`} row={row} currentTick={citizen.currentTick} onSelectIncident={onSelectIncident} />
                ))}
              </section>
            </div>
          ) : (
            <div className="profile-grid profile-grid-justice">
              <section className="profile-section">
                <h3>Situation pénale</h3>
                <dl className="profile-facts">
                  <div><dt>Infractions commises</dt><dd>{citizen.criminality.offensesCommitted}</dd></div>
                  <div><dt>Arrestations</dt><dd>{citizen.criminality.arrests}</dd></div>
                  <div><dt>Victimisations</dt><dd>{citizen.criminality.victimizations}</dd></div>
                  <div><dt>Statut</dt><dd>{citizen.justice.detained ? "Retenu" : "Libre"}</dd></div>
                </dl>
              </section>

              <section className="profile-section profile-section-wide">
                <h3>Historique des mesures policières</h3>
                {citizen.justice.policeHistory.length === 0 ? <p className="muted">Aucune mesure policière.</p> : (
                  <div className="justice-list">
                    {citizen.justice.policeHistory.map((measure, index) => (
                      <article className="justice-card" key={`${measure.tick}-${measure.incidentId}-${index}`}>
                        <header><strong>{measure.label}</strong><span>Incident #{measure.incidentId}</span></header>
                        <p>{measure.reason}</p>
                        <dl>
                          <div><dt>Durée</dt><dd>{measure.durationMinutes > 0 ? `${measure.durationMinutes} min` : "Aucune rétention"}</dd></div>
                          <div><dt>Agents</dt><dd>{measure.officers.filter(Boolean).map((officer) => officer!.name).join(", ") || "Non renseignés"}</dd></div>
                        </dl>
                        <button onClick={() => onSelectIncident(measure.incidentId)}>Ouvrir l’incident</button>
                      </article>
                    ))}
                  </div>
                )}
              </section>

              <section className="profile-section">
                <h3>Enquêtes associées</h3>
                {citizen.justice.investigations.length === 0 ? <p className="muted">Aucune enquête.</p> : (
                  <div className="justice-list">
                    {citizen.justice.investigations.map((investigation) => (
                      <article className="justice-card" key={investigation.id}>
                        <header><strong>Enquête #{investigation.id}</strong><span>{INVESTIGATION_LABELS[investigation.status] ?? investigation.status}</span></header>
                        <p>Confiance des enquêteurs : {Math.round(investigation.confidence)} %</p>
                        <button onClick={() => onSelectIncident(investigation.incidentId)}>Incident #{investigation.incidentId}</button>
                      </article>
                    ))}
                  </div>
                )}
              </section>

              <section className="profile-section profile-section-wide">
                <h3>Dossiers judiciaires</h3>
                {citizen.justice.cases.length === 0 ? <p className="muted">Aucun dossier judiciaire.</p> : (
                  <div className="justice-list justice-list-cases">
                    {citizen.justice.cases.map((row) => <CaseCard key={row.id} row={row} currentTick={citizen.currentTick} onSelectCase={onSelectCase} />)}
                  </div>
                )}
              </section>
              <section className="profile-section profile-section-wide">
                <h3>Peines et mesures en cours</h3>
                {citizen.justice.sentences.length === 0 ? <p className="muted">Aucune peine enregistrée.</p> : (
                  <div className="justice-list">
                    {citizen.justice.sentences.map((sentence) => (
                      <article className="justice-card" key={sentence.id}>
                        <header><strong>{sentence.label}</strong><span>{sentence.status}</span></header>
                        {sentence.requiredMinutes > 0 && <p>Progression : {sentence.completedMinutes} / {sentence.requiredMinutes} min</p>}
                        {sentence.violationCount > 0 && <p className="conflict-outcome">Violations : {sentence.violationCount}</p>}
                        <button onClick={() => onSelectCase(sentence.caseId)}>Dossier #{sentence.caseId}</button>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
