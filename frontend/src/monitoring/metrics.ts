import type { CitySnapshot } from "../types/city";

export type MetricTone =
  | "neutral"
  | "housing"
  | "economy"
  | "health"
  | "mobility"
  | "social"
  | "security"
  | "banking"
  | "neighborhoods";
export type MetricGroupId =
  | "summary"
  | "housing"
  | "economy"
  | "health"
  | "mobility"
  | "social"
  | "security"
  | "banking"
  | "neighborhoods";
export type CityStats = CitySnapshot["stats"];

export interface MetricCardModel {
  id: string;
  label: string;
  value: string;
  tone: MetricTone;
}

export interface MetricGroupModel {
  id: MetricGroupId;
  label: string;
  metrics: MetricCardModel[];
}

const euro = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});
const number = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });
const MOVING_ACTIVITIES = ["walking", "driving", "riding_bus", "waiting_bus"] as const;

const card = (
  id: string,
  label: string,
  value: string,
  tone: MetricTone,
): MetricCardModel => ({ id, label, value, tone });

const movingCitizens = (stats: CityStats) => MOVING_ACTIVITIES.reduce(
  (total, activity) => total + (stats.activityCounts[activity] ?? 0),
  0,
);

export function buildMetricGroups(stats: CityStats): MetricGroupModel[] {
  const moving = number.format(movingCitizens(stats));
  return [
    {
      id: "summary",
      label: "Synthèse",
      metrics: [
        card("population", "Population", number.format(stats.population), "neutral"),
        card("unemployment", "Chômage", `${number.format(stats.unemploymentRate)} %`, "economy"),
        card("housing-distress", "Foyers en difficulté", number.format(stats.distressedHouseholds), "housing"),
        card("emergencies", "Urgences médicales", number.format(stats.medicalEmergencies), "health"),
        card("moving", "Habitants en déplacement", moving, "mobility"),
        card("incidents", "Incidents actifs", number.format(stats.activeIncidents), "security"),
      ],
    },
    {
      id: "housing",
      label: "Logement",
      metrics: [
        card("rent", "Loyer médian", euro.format(stats.medianRent), "housing"),
        card("vacancy", "Vacance résidentielle", `${number.format(stats.vacancyRate)} %`, "housing"),
        card("overcrowded", "Foyers surpeuplés", number.format(stats.overcrowdedHouseholds), "housing"),
        card("distressed", "Foyers en difficulté", number.format(stats.distressedHouseholds), "housing"),
        card("homeless", "Personnes sans abri", number.format(stats.homelessCitizens), "housing"),
        card("moves", "Déménagements du jour", number.format(stats.movesToday), "housing"),
      ],
    },
    {
      id: "economy",
      label: "Économie",
      metrics: [
        card("money", "Argent moyen", euro.format(stats.averageMoney), "economy"),
        card("unemployment", "Taux de chômage", `${number.format(stats.unemploymentRate)} %`, "economy"),
        card("positions", "Postes vacants", number.format(stats.openPositions), "economy"),
        card("deficit", "Entreprises déficitaires", number.format(stats.deficitBusinesses), "economy"),
        card("salary", "Salaire médian", euro.format(stats.medianSalary), "economy"),
        card("income", "Revenu médian des foyers", euro.format(stats.medianHouseholdIncome), "economy"),
      ],
    },
    {
      id: "banking",
      label: "Banque",
      metrics: [
        card("deposits", "Dépôts", euro.format(stats.deposits), "banking"),
        card("savings", "Épargne", euro.format(stats.savings), "banking"),
        card("debt", "Crédits citoyens", euro.format(stats.citizenDebt), "banking"),
        card("borrowers", "Emprunteurs", number.format(stats.borrowers), "banking"),
        card("loans", "Crédits du jour", euro.format(stats.loansIssuedToday), "banking"),
        card("defaults", "Impayés du jour", euro.format(stats.defaultsToday), "banking"),
      ],
    },
    {
      id: "health",
      label: "Santé",
      metrics: [
        card("emergencies", "Urgences médicales", number.format(stats.medicalEmergencies), "health"),
        card("waiting", "File d’attente", number.format(stats.patientsWaiting), "health"),
        card("hospitalized", "Hospitalisés", `${stats.hospitalizedPatients} / ${stats.hospitalBeds}`, "health"),
        card("staff", "Soignants en service", number.format(stats.medicalStaffOnDuty), "health"),
        card("ambulances", "Ambulances disponibles", number.format(stats.ambulancesAvailable), "health"),
        card("wait", "Attente moyenne", `${number.format(stats.averageMedicalWaitMinutes)} min`, "health"),
      ],
    },
    {
      id: "mobility",
      label: "Mobilité",
      metrics: [
        card("moving", "En déplacement", moving, "mobility"),
        card("vehicles", "Véhicules actifs", number.format(stats.movingVehicles), "mobility"),
        card("passengers", "Passagers bus", number.format(stats.busPassengers), "mobility"),
        card("boardings", "Montées bus", number.format(stats.busBoardingsToday), "mobility"),
        card("delay", "Retard trafic", `${number.format(stats.trafficDelayToday)} min`, "mobility"),
        card("trip", "Trajet moyen", `${number.format(stats.averageTripMinutes)} min`, "mobility"),
      ],
    },
    {
      id: "social",
      label: "Social",
      metrics: [
        card("friendships", "Amitiés", number.format(stats.friendships), "social"),
        card("rivalries", "Rivalités", number.format(stats.rivalries), "social"),
        card("communications", "Communications du jour", number.format(stats.sentToday), "social"),
        card("cohesion", "Cohésion des foyers", `${number.format(stats.averageHouseholdCohesion)} %`, "social"),
        card("isolated", "Habitants isolés", number.format(stats.isolatedCitizens), "social"),
        card("network", "Réseau moyen", number.format(stats.averageSocialNetwork), "social"),
      ],
    },
    {
      id: "neighborhoods",
      label: "Quartiers",
      metrics: [
        card("district-safety", "Sécurité moyenne", `${number.format(stats.averageNeighborhoodSafety)} %`, "neighborhoods"),
        card("district-gap", "Écart de sécurité", `${number.format(stats.neighborhoodSafetyGap)} pts`, "neighborhoods"),
        card("district-attractiveness", "Attractivité moyenne", `${number.format(stats.averageNeighborhoodAttractiveness)} %`, "neighborhoods"),
        card("district-pressure", "Pression maximale", `${number.format(stats.highestServicePressure)} %`, "neighborhoods"),
        card("district-response", "Réponse la plus lente", `${number.format(stats.slowestNeighborhoodResponseMinutes)} min`, "neighborhoods"),
        card("district-health", "Accès soins minimal", `${number.format(stats.lowestHealthcareAccess)} %`, "neighborhoods"),
      ],
    },
    {
      id: "security",
      label: "Sécurité",
      metrics: [
        card("factions", "Factions criminelles", number.format(stats.organizations), "security"),
        card("members", "Membres identifiés", number.format(stats.factionMembers), "security"),
        card("illegal-sales", "Ventes illégales du jour", number.format(stats.illegalSalesToday), "security"),
        card("dependent", "Citoyens dépendants", number.format(stats.dependentCitizens), "security"),
        card("territories", "Quartiers disputés", number.format(stats.contestedNeighborhoods), "security"),
        card("investigations", "Enquêtes ouvertes", number.format(stats.openInvestigations), "security"),
      ],
    },
  ];
}