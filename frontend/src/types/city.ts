export type Activity =
  | "sleeping"
  | "working"
  | "walking"
  | "driving"
  | "waiting_bus"
  | "riding_bus"
  | "eating"
  | "relaxing"
  | "at_home"
  | "detained"
  | "shopping"
  | "waiting_medical"
  | "in_treatment"
  | "hospitalized";

export type TransportMode = "walk" | "car" | "bus";
export type TravelStage =
  | "idle"
  | "walking"
  | "to_bus_stop"
  | "waiting_bus"
  | "on_bus"
  | "from_bus_stop"
  | "driving";

export type RelationshipStatus = "unknown" | "acquaintance" | "friend" | "close_friend" | "rival";
export type SocialEventType = "coffee" | "park_meetup";
export type SocialEventStatus = "planned" | "active" | "completed" | "cancelled";
export type IncidentStatus = "active" | "reported" | "responding" | "on_scene" | "resolved" | "expired";
export type VehicleType = "car" | "bus" | "police" | "ambulance";
export type VehicleStatus =
  | "parked"
  | "driving"
  | "in_service"
  | "stopped"
  | "responding"
  | "on_scene"
  | "returning"
  | "transporting";

export type BusinessStatus = "healthy" | "fragile" | "deficit" | "closed";
export type JobApplicationStatus = "pending" | "accepted" | "rejected" | "withdrawn";

export interface EmploymentRecord {
  tick: number;
  eventType: string;
  label: string;
  buildingId: number | null;
  jobTitle: string | null;
  salaryDaily: number;
  reason: string;
}

export interface JobApplicationSummary {
  id: number;
  citizenId: number;
  building: { id: number; name: string };
  jobTitle: string;
  salaryDaily: number;
  submittedTick: number;
  score: number;
  status: JobApplicationStatus;
  resolvedTick: number | null;
  reason: string | null;
}

export interface BusinessFinancialRecord {
  day: number;
  revenue: number;
  payroll: number;
  fixedCosts: number;
  result: number;
  cash: number;
  serviceLevel: number;
  status: BusinessStatus;
}

export interface HouseholdFinancialRecord {
  day: number;
  income: number;
  recurringExpenses: number;
  foodExpenses: number;
  goodsExpenses: number;
  debt: number;
  financialStress: number;
}

export interface CitizenSummary {
  id: number;
  name: string;
  x: number;
  y: number;
  activity: Activity;
  destinationBuildingId: number | null;
  transportMode: TransportMode;
  travelStage: TravelStage;
  activeVehicleId: number | null;
  socialEventId: number | null;
  friendCount: number;
  jobTitle: string | null;
  onDuty: boolean;
  health: number;
  healthCondition: "healthy" | "minor_injury" | "serious_injury" | "mild_illness" | "severe_illness" | "recovering";
  careStatus: string;
  pain: number;
  activeHealthCaseId: number | null;
}

export interface BuildingSummary {
  id: number;
  name: string;
  type: "home" | "office" | "factory" | "shop" | "cafe" | "park" | "public" | "police" | "hospital";
  x: number;
  y: number;
  width: number;
  height: number;
  capacity: number;
  occupancy: number;
  employeesRequired: number;
  staffOnDuty: number;
  operational: boolean;
  foodStock: number;
  goodsStock: number;
  revenueToday: number;
  cash: number;
  payrollToday: number;
  fixedCostsToday: number;
  resultToday: number;
  serviceLevel: number;
  businessStatus: BusinessStatus;
  assignedEmployees: number;
  employeeCapacity: number;
  targetEmployees: number;
  openPositions: number;
  medicalBeds: number;
  patientsWaiting: number;
  hospitalizedPatients: number;
  patientsTreatedToday: number;
}

export interface VehicleSummary {
  id: number;
  type: VehicleType;
  x: number;
  y: number;
  status: VehicleStatus;
  occupancy: number;
  capacity: number;
  ownerId: number | null;
  lineId: number | null;
  crewIds: number[];
  healthCaseId: number | null;
}

export interface BusStopSummary {
  id: number;
  name: string;
  x: number;
  y: number;
  lineId: number;
  sequence: number;
}

export interface BusLineSummary {
  id: number;
  name: string;
  stopIds: number[];
  route: Array<{ x: number; y: number }>;
  fare: number;
}

export interface SocialEventSummary {
  id: number;
  type: SocialEventType;
  status: SocialEventStatus;
  host: { id: number; name: string };
  participants: Array<{ id: number; name: string }>;
  building: { id: number; name: string };
  plannedTick: number;
  minutesUntilStart: number;
  durationMinutes: number;
}

export interface HouseholdSummary {
  id: number;
  homeId: number;
  homeName: string;
  members: number;
  cohesion: number;
  sharedMeals: number;
  conflicts: number;
  incomeToday: number;
  expensesToday: number;
  debt: number;
  financialStress: number;
}

export interface IncidentSummary {
  id: number;
  type: string;
  title: string;
  severity: "warning" | "danger";
  status: IncidentStatus;
  x: number;
  y: number;
  buildingId: number | null;
  vehicleId: number | null;
  citizenIds: number[];
  reported: boolean;
  policeVehicleId: number | null;
  createdTick: number;
  remainingMinutes: number;
  conflictLevel: number;
  investigationId: number | null;
  policeAction: string | null;
  policeOfficerIds: number[];
  detainedIds: number[];
}

export interface HealthCaseSummary {
  id: number; citizen: { id: number; name: string }; source: string; severity: number; status: string; hospitalId: number | null; ambulanceId: number | null; incidentId: number | null; createdTick: number; waitingMinutes: number;
}

export interface HealthOverview {
  tick: number;
  metrics: { activeMedicalCases: number; medicalEmergencies: number; patientsWaiting: number; hospitalizedPatients: number; hospitalBeds: number; medicalStaffOnDuty: number; ambulancesAvailable: number; ambulanceDispatchesToday: number; averageMedicalWaitMinutes: number };
  hospital: { id: number; name: string } | null; cases: HealthCaseSummary[];
}

export interface CityEvent {
  id: number;
  tick: number;
  day: number;
  hour: number;
  minute: number;
  time: string;
  eventType: string;
  message: string;
  citizenIds: number[];
  buildingId: number | null;
  vehicleId: number | null;
  severity: "info" | "warning" | "danger";
  incidentId: number | null;
}

export interface EconomyMetrics {
  unemployedCitizens: number;
  unemploymentRate: number;
  openPositions: number;
  deficitBusinesses: number;
  closedBusinesses: number;
  medianSalary: number;
  medianHouseholdIncome: number;
  hiresToday: number;
  layoffsToday: number;
  resignationsToday: number;
  publicSpendingTotal: number;
}

export interface EconomyBusinessSummary {
  id: number;
  name: string;
  type: BuildingSummary["type"];
  status: BusinessStatus;
  cash: number;
  revenueToday: number;
  payrollToday: number;
  fixedCostsToday: number;
  resultToday: number;
  serviceLevel: number;
  employees: number;
  employeesRequired: number;
  employeeCapacity: number;
  openPositions: number;
}

export interface EconomyOverview {
  tick: number;
  metrics: EconomyMetrics;
  businesses: EconomyBusinessSummary[];
}

export interface CitySnapshot {
  type: "city_snapshot";
  tick: number;
  day: number;
  hour: number;
  minute: number;
  timeLabel: string;
  map: { width: number; height: number };
  stats: EconomyMetrics & {
    population: number;
    averageMoney: number;
    reportedIncidents: number;
    activeIncidents: number;
    seriousIncidents: number;
    policeUnitsAvailable: number;
    policeOfficersOnDuty: number;
    staffedPatrols: number;
    policeWarningsToday: number;
    policeDetentionsToday: number;
    policeResponsesToday: number;
    averagePoliceResponseMinutes: number;
    openInvestigations: number;
    suspectsIdentified: number;
    arrestsToday: number;
    casesFiledToday: number;
    casesAwaitingHearing: number;
    casesDecided: number;
    employedCitizens: number;
    workersOnDuty: number;
    operationalWorkplaces: number;
    averageJobPerformance: number;
    shoppingTripsToday: number;
    shopSalesToday: number;
    marketFoodStock: number;
    marketGoodsStock: number;
    activeMedicalCases: number; medicalEmergencies: number; patientsWaiting: number; hospitalizedPatients: number; hospitalBeds: number; medicalStaffOnDuty: number; ambulancesAvailable: number; ambulanceDispatchesToday: number; averageMedicalWaitMinutes: number;
    activityCounts: Record<string, number>;
    transportModeCounts: Record<TransportMode, number>;
    tripCountsToday: Record<TransportMode, number>;
    carOwners: number;
    movingVehicles: number;
    busPassengers: number;
    busBoardingsToday: number;
    trafficDelayToday: number;
    averageTripMinutes: number;
    households: number;
    averageHouseholdCohesion: number;
    friendships: number;
    rivalries: number;
    isolatedCitizens: number;
    averageSocialNetwork: number;
    socialInvitationsToday: number;
    socialAcceptancesToday: number;
    activeSocialEvents: number;
    socialGatheringsCompleted: number;
  };
  citizens: CitizenSummary[];
  buildings: BuildingSummary[];
  vehicles: VehicleSummary[];
  roads: {
    cells: Array<{ x: number; y: number }>;
    congestion: Array<{
      x: number;
      y: number;
      vehicles: number;
      level: "moderate" | "heavy";
    }>;
  };
  transport: {
    busStops: BusStopSummary[];
    busLines: BusLineSummary[];
    operating: boolean;
  };
  social: {
    events: SocialEventSummary[];
    households: HouseholdSummary[];
  };
  economy: EconomyOverview;
  health: HealthOverview;
  incidents: IncidentSummary[];
  events: CityEvent[];
  simulation: {
    paused: boolean;
    speed: number;
    allowedSpeeds: number[];
    hasSave: boolean;
  };
}

export type CityDelta = Pick<
  CitySnapshot,
  | "tick"
  | "day"
  | "hour"
  | "minute"
  | "timeLabel"
  | "stats"
  | "citizens"
  | "buildings"
  | "vehicles"
  | "social"
  | "economy"
  | "health"
  | "incidents"
  | "events"
  | "simulation"
> & {
  type: "city_delta";
  roads: Pick<CitySnapshot["roads"], "congestion">;
  transport: Pick<CitySnapshot["transport"], "operating">;
};

export type CityStreamMessage = CitySnapshot | CityDelta;

export interface CitizenDetail extends CitizenSummary {
  kind: "citizen";
  currentTick: number;
  age: number;
  home: { id: number; name: string };
  workplace: { id: number; name: string } | null;
  destination: { id: number; name: string } | null;
  jobTitle: string | null;
  salaryDaily: number;
  money: number;
  health: number;
  medical: { condition: CitizenSummary["healthCondition"]; careStatus: string; pain: number; injurySeverity: number; illnessSeverity: number; activeCaseId: number | null; medicalLeaveUntilTick: number | null; incapacityUntilTick: number | null; hospitalizedUntilTick: number | null; history: Array<{ tick: number; eventType: string; label: string; severity: number; source: string; incidentId: number | null; hospitalId: number | null; incapacityMinutes: number }> };
  employment: {
    status: "employed" | "unemployed";
    workStartHour: number;
    workEndHour: number;
    workDays: number[];
    scheduledToday: boolean;
    onDuty: boolean;
    minutesWorkedToday: number;
    shiftsCompleted: number;
    missedShifts: number;
    performance: number;
    satisfaction: number;
    jobSearchActive: boolean;
    jobSearchSinceTick: number | null;
    lastJobChangeTick: number;
    incomeToday: number;
    expensesToday: number;
    financialStress: number;
    experienceByJob: Record<string, number>;
    applications: JobApplicationSummary[];
    history: EmploymentRecord[];
  };
  consumption: {
    foodUnits: number;
    goodsUnits: number;
    shoppingVisits: number;
    lastShoppingTick: number | null;
    intoxication: number;
  };
  criminality: {
    offensesCommitted: number;
    victimizations: number;
    arrests: number;
  };
  needs: {
    hunger: number;
    fatigue: number;
    stress: number;
    social: number;
  };
  decisionReason: string;
  relationships: Array<{
    citizenId: number;
    name: string;
    familiarity: number;
    affection: number;
    trust: number;
    status: RelationshipStatus;
    positiveInteractions: number;
    negativeInteractions: number;
    lastInteractionTick: number;
    consecutiveNegativeInteractions: number;
    conflictScore: number;
    conflictLevel: number;
    conflictLabel: string;
    peakConflictLevel: number;
    lastConflictTick: number | null;
    conflictHistory: ConflictHistoryEntry[];
  }>;
  personality: {
    sociability: number;
    agreeableness: number;
    spontaneity: number;
    aggression: number;
    impulsivity: number;
    grudgeTendency: number;
    conflictPropensity: number;
    temperament: string;
  };
  household: {
    id: number;
    homeId: number;
    cohesion: number;
    sharedMeals: number;
    conflicts: number;
    incomeToday: number;
    recurringExpensesToday: number;
    foodExpensesToday: number;
    goodsExpensesToday: number;
    debt: number;
    overdraftLimit: number;
    financialStress: number;
    budgets: {
      foodDaily: number;
      goodsDaily: number;
    };
    financialHistory: HouseholdFinancialRecord[];
    members: Array<{ id: number; name: string }>;
  } | null;
  social: {
    interactionsToday: number;
    invitationsSent: number;
    invitationsAccepted: number;
    favoritePlaces: Array<{ id: number; name: string; visits: number }>;
    event: SocialEventSummary | null;
  };
  conflictHistory: ConflictHistoryEntry[];
  justice: {
    detained: boolean;
    detainedUntilTick: number | null;
    detentionType: string | null;
    policeHistory: Array<{
      tick: number;
      incidentId: number;
      measureType: string;
      label: string;
      durationMinutes: number;
      reason: string;
      officers: Array<{ id: number; name: string } | null>;
    }>;
    investigations: Array<{
      id: number;
      incidentId: number;
      status: InvestigationStatus;
      confidence: number;
      openedTick: number;
      caseId: number | null;
    }>;
    cases: JudicialCaseSummary[];
  };
  transport: {
    mode: TransportMode;
    lastMode: TransportMode;
    stage: TravelStage;
    ownedVehicle: { id: number; type: VehicleType } | null;
    activeVehicle: { id: number; type: VehicleType } | null;
    originStop: { id: number; name: string } | null;
    destinationStop: { id: number; name: string } | null;
    lastTripMinutes: number;
    travelMinutesToday: number;
    tripsToday: number;
  };
}

export interface VehicleDetail extends VehicleSummary {
  kind: "vehicle";
  owner: { id: number; name: string } | null;
  line: { id: number; name: string } | null;
  target: { id: number; name: string } | null;
  passengers: Array<{ id: number; name: string }>;
  crew: Array<{ id: number; name: string; onDuty: boolean }>;
  delayMinutes: number;
  distanceToday: number;
  routeProgress: number;
  incident: { id: number; title: string } | null;
}

export interface IncidentDetail extends IncidentSummary {
  kind: "incident";
  description: string;
  building: { id: number; name: string } | null;
  offender: { id: number; name: string } | null;
  victims: Array<{ id: number; name: string } | null>;
  witnesses: Array<{ id: number; name: string } | null>;
  involved: Array<{ id: number; name: string } | null>;
  policeVehicle: { id: number; type: VehicleType } | null;
  timeline: {
    createdTick: number;
    dispatchedTick: number | null;
    arrivalTick: number | null;
    resolvedTick: number | null;
  };
  resolution: string | null;
  policeAction: string | null;
  policeOfficers: Array<{ id: number; name: string } | null>;
  detained: Array<{ id: number; name: string } | null>;
  investigation: InvestigationDetail | null;
  healthCases: HealthCaseSummary[];
}

export interface BuildingDetail extends BuildingSummary {
  kind: "building";
  employees: Array<{
    id: number;
    name: string;
    jobTitle: string | null;
    onDuty: boolean;
    shift: string;
    performance: number;
    satisfaction: number;
  }>;
  occupants: Array<{ id: number; name: string }>;
  healthcare: { beds: number; queue: HealthCaseSummary[]; hospitalized: Array<{ id: number; name: string } | null>; patientsTreatedToday: number; ambulances: VehicleSummary[] } | null;
  services: {
    operational: boolean;
    staffOnDuty: number;
    employeesRequired: number;
    foodStock: number;
    goodsStock: number;
    revenueToday: number;
  };
  finance: {
    status: BusinessStatus;
    cash: number;
    totalRevenue: number;
    payrollToday: number;
    fixedCostsToday: number;
    resultToday: number;
    serviceLevel: number;
    employeeCapacity: number;
    targetEmployees: number;
    openPositions: number;
    financialHistory: BusinessFinancialRecord[];
    employmentHistory: EmploymentRecord[];
  };
}

export type InvestigationStatus = "open" | "suspect_identified" | "arrested" | "referred" | "closed";
export type JudicialCaseStatus = "filed" | "awaiting_hearing" | "decided" | "dismissed";

export interface ConflictHistoryEntry {
  otherId?: number;
  otherName?: string;
  tick: number;
  level: number;
  label: string;
  title: string;
  incidentId: number | null;
  buildingId: number | null;
  buildingName: string | null;
  role: string;
  outcome: string | null;
}

export interface EvidenceDetail {
  id: number;
  type: string;
  description: string;
  reliability: number;
  citizen: { id: number; name: string } | null;
  createdTick: number;
}

export interface JudicialCaseSummary {
  id: number;
  investigationId: number;
  incidentId: number;
  defendant: { id: number; name: string } | null;
  charges: string[];
  status: JudicialCaseStatus;
  filedTick: number;
  hearingTick: number;
  evidenceScore: number;
  decidedTick: number | null;
  verdict: string | null;
  sentence: string | null;
  defendantName: string | null;
}

export interface InvestigationDetail {
  id: number;
  incidentId: number;
  status: InvestigationStatus;
  openedTick: number;
  updatedTick: number;
  suspects: Array<{ id: number; name: string } | null>;
  leadSuspect: { id: number; name: string } | null;
  confidence: number;
  arrestTick: number | null;
  notes: string[];
  evidence: EvidenceDetail[];
  case: JudicialCaseSummary | null;
}

export interface SocialGraphData {
  tick: number;
  nodes: Array<{
    id: number;
    name: string;
    householdId: number | null;
    workplaceId: number | null;
    friendCount: number;
    rivalCount: number;
    conflictPropensity: number;
    temperament: string;
  }>;
  edges: Array<{
    source: number;
    target: number;
    status: RelationshipStatus;
    affection: number;
    trust: number;
    familiarity: number;
    conflictLevel: number;
    conflictLabel: string;
  }>;
}

export type InspectorEntity = CitizenDetail | VehicleDetail | IncidentDetail | BuildingDetail;
export type SelectedEntity = { kind: "citizen" | "vehicle" | "incident" | "building"; id: number };
