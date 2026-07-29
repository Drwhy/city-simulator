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
  | "hospitalized"
  | "community_service"
  | "kidnapped";

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
  crimeOrganizationId: number | null;
  criminalRole: string | null;
  addictionLevel: number;
  substanceUseRisk: number;
}

export interface BuildingSummary {
  id: number;
  name: string;
  type: "home" | "office" | "factory" | "shop" | "cafe" | "park" | "public" | "police" | "hospital" | "court" | "detention_center" | "bank" | "shelter";
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
  housing: HomeSummary | null;
  neighborhoodId: number;
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
  patrolNeighborhoodId: number | null;
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
  status: "stable" | "searching" | "temporary" | "homeless";
  rentMonthly: number;
  rentArrears: number;
  incomeMonthly: number;
  commonBudget: number;
  overcrowded: boolean;
  commuteDistance: number;
  moves: number;
  searchReason: string | null;
}

export interface HousingRecord { tick: number; eventType: string; label: string; fromHomeId: number | null; toHomeId: number; reason: string; rentBefore: number; rentAfter: number; memberIds: number[]; }
export interface HomeSummary { id: number; name: string; capacity: number; residentCount: number; availablePlaces: number; rentMonthly: number; condition: number; comfort: number; ownerType: string; serviceDistance: number; safety: number; available: boolean; }
export interface HousingMetrics { medianRent: number; vacancyRate: number; overcrowdedHouseholds: number; distressedHouseholds: number; movesToday: number; averageHomeWorkDistance: number; searchingHouseholds: number; temporaryHouseholds: number; homelessCitizens: number; homelessHouseholds: number; }
export interface HousingOverview { tick: number; metrics: HousingMetrics; homes: HomeSummary[]; households: HouseholdSummary[]; }
export interface HouseholdDetail extends HouseholdSummary { kind: "household"; membersList: Array<{id:number;name:string}|null>; expenses: { recurringToday:number; foodToday:number; goodsToday:number; rentDueToday:number; rentPaidToday:number }; reserves:number; home:HomeSummary; financialHistory:HouseholdFinancialRecord[]; housingHistory:HousingRecord[]; temporaryHostHouseholdId:number|null; }

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
  neighborhoodId: number;
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

export type CommunicationChannel = "phone_call" | "sms" | "email" | "letter";
export type CommunicationTone = "friendly" | "practical" | "apology" | "invitation" | "conflict";
export type CommunicationStatus = "queued" | "ringing" | "delivered" | "read" | "replied" | "failed";
export interface CommunicationSummary {
  id: number; threadId: number; sender: { id: number; name: string }; recipient: { id: number; name: string };
  channel: CommunicationChannel; tone: CommunicationTone; subject: string; body: string; status: CommunicationStatus;
  createdTick: number; deliveryTick: number; readTick: number | null; repliedTick: number | null; replyToId: number | null; replyDepth: number;
  durationMinutes: number; cost: number; failureReason: string | null; violatesOrder: boolean;
}
export interface CommunicationMetrics { sentToday: number; deliveredToday: number; phoneCallsToday: number; smsToday: number; emailsToday: number; lettersToday: number; unreadCommunications: number; communicationRepliesToday: number; }
export interface CommunicationOverview { metrics: CommunicationMetrics; recent: CommunicationSummary[]; }

export interface NeighborhoodSummary {
  id: number; name: string; bounds: { xMin: number; yMin: number; xMax: number; yMax: number }; lighting: number;
  population: number; averageIncome: number; unemploymentRate: number; averageRent: number; commercialActivity: number;
  criminality: number; safetyPerception: number; policeCoverage: number; averageResponseMinutes: number;
  healthcareAccess: number; commerceAccess: number; averageTransportMinutes: number; attractiveness: number; servicePressure: number;
}
export interface NeighborhoodOverview { tick: number; neighborhoods: NeighborhoodSummary[]; metrics: { averageSafety: number; averageAttractiveness: number; highestServicePressure: number; slowestResponseMinutes: number; lowestHealthcareAccess: number; safetyGap: number }; }
export interface NeighborhoodDetail extends NeighborhoodSummary {
  kind: "neighborhood";
  buildings: Array<{ id: number; name: string; type: BuildingSummary["type"]; serviceLevel: number }>;
  businesses: Array<{ id: number; name: string; type: BuildingSummary["type"]; revenueToday: number; serviceLevel: number }>;
  services: Array<{ id: number; name: string; type: BuildingSummary["type"]; serviceLevel: number }>;
  incidents: IncidentSummary[]; patrols: VehicleSummary[];
  history: Array<Omit<NeighborhoodSummary, "id" | "name" | "bounds" | "lighting"> & { day: number }>;
}

export interface CrimeMetrics {
  organizations: number; factionMembers: number; criminalMarkets: number; operations: number;
  organizedCrimesToday: number; activeKidnappings: number; ransomPaidToday: number;
  illegalSalesToday: number; drugSalesToday: number; illegalRevenueToday: number;
  policeSeizuresToday: number; exposedCitizens: number; dependentCitizens: number;
  highRiskCitizens: number; contestedNeighborhoods: number; detectedTransactions: number;
}
export interface CrimeOrganizationSummary {
  id:number; name:string; factionType:string; leaderId:number; leaderName:string; memberCount:number;
  territoryId:number; territoryIds:number[]; treasury:number; revenueToday:number; expensesToday:number;
  notoriety:number; policeHeat:number; cohesion:number; violence:number; sophistication:number;
  recruitmentPressure:number; membersRecruited:number; specialties:string[]; inventory:Record<string,number>;
  rivalIds:number[]; allyIds:number[]; marketCount:number; customers:number; active:boolean;
}
export interface CriminalMarketSummary {
  id:number; organizationId:number; organizationName:string; neighborhoodId:number; neighborhoodName:string;
  commodity:string; supply:number; demand:number; unitPrice:number; policePressure:number;
  transactionsToday:number; revenueToday:number; seizedToday:number; drugMarket:boolean; active:boolean;
}
export interface IllegalTransactionSummary {
  id:number; tick:number; organizationId:number; organizationName:string; marketId:number;
  seller:{id:number;name:string}; buyer:{id:number;name:string}; commodity:string; quantity:number;
  unitPrice:number; total:number; neighborhoodId:number; buildingId:number|null; detected:boolean; incidentId:number|null;
}
export interface CrimeOperationSummary {
  id:number; organizationId:number; organizationName:string; type:string; status:string; perpetratorIds:number[];
  victimIds:number[]; buildingId:number|null; neighborhoodId:number|null; commodity:string|null; quantity:number;
  amount:number; detected:boolean; incidentId:number|null; startedTick:number|null; resolvedTick:number|null; outcome:string|null;
}
export interface CrimeOverview {
  tick:number; metrics:CrimeMetrics; organizations:CrimeOrganizationSummary[]; markets:CriminalMarketSummary[];
  transactions:IllegalTransactionSummary[]; operations:CrimeOperationSummary[];
  relations:Array<{firstId:number;firstName:string;secondId:number;secondName:string;tension:number;trust:number;conflictCount:number;lastConflictTick:number|null;truceUntilTick:number|null}>;
  territories:Array<{neighborhoodId:number;neighborhoodName:string;contestedness:number;factions:Array<{organizationId:number;name:string;influence:number}>}>;
  commodities:Array<{commodity:string;transactions:number;revenue:number;supply:number}>;
  history:Array<{day:number;organizedCrimes:number;illegalSales:number;drugSales:number;illegalRevenue:number;policeSeizures:number;dependentCitizens:number}>;
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
    complaintsFiled: number;
    hearingsToday: number;
    courtCapacityToday: number;
    courtStaffOnDuty: number;
    activeSentences: number;
    citizensOnProbation: number;
    restrainingOrders: number;
    detainedCitizens: number;
    detentionCapacity: number;
    probationViolationsToday: number;
    employedCitizens: number;
    workersOnDuty: number;
    operationalWorkplaces: number;
    averageJobPerformance: number;
    shoppingTripsToday: number;
    shopSalesToday: number;
    marketFoodStock: number;
    marketGoodsStock: number;
    activeMedicalCases: number; medicalEmergencies: number; patientsWaiting: number; hospitalizedPatients: number; hospitalBeds: number; medicalStaffOnDuty: number; ambulancesAvailable: number; ambulanceDispatchesToday: number; averageMedicalWaitMinutes: number;
    medianRent: number; vacancyRate: number; overcrowdedHouseholds: number; distressedHouseholds: number; movesToday: number; averageHomeWorkDistance: number; searchingHouseholds: number; temporaryHouseholds: number; homelessCitizens: number; homelessHouseholds: number;
    deposits: number; savings: number; citizenDebt: number; borrowers: number; loansIssuedToday: number; defaultsToday: number;
    organizations: number; factionMembers: number; criminalMarkets: number; operations: number; organizedCrimesToday: number; activeKidnappings: number; ransomPaidToday: number; illegalSalesToday: number; drugSalesToday: number; illegalRevenueToday: number; policeSeizuresToday: number; exposedCitizens: number; dependentCitizens: number; highRiskCitizens: number; contestedNeighborhoods: number; detectedTransactions: number;
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
    sentToday: number; deliveredToday: number; phoneCallsToday: number; smsToday: number; emailsToday: number; lettersToday: number; unreadCommunications: number; communicationRepliesToday: number;
    averageNeighborhoodSafety: number; averageNeighborhoodAttractiveness: number; highestServicePressure: number; slowestNeighborhoodResponseMinutes: number; lowestHealthcareAccess: number; neighborhoodSafetyGap: number;
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
  banking: { tick: number; bank: { id: number | null; name: string | null; reserves: number; outstandingLoans: number; interestIncome: number }; metrics: { deposits: number; savings: number; citizenDebt: number; borrowers: number; loansIssuedToday: number; defaultsToday: number } };
  crime: CrimeOverview;
  health: HealthOverview;
  housing: HousingOverview;
  justice: JusticeOverview;
  communications: CommunicationOverview;
  neighborhoods: NeighborhoodOverview;
  incidents: IncidentSummary[];
  events: CityEvent[];
  simulation: {
    paused: boolean;
    speed: number;
    allowedSpeeds: number[];
    hasSave: boolean;
    citizenCount: number;
    maxCitizenCount: number;
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
  | "banking"
  | "crime"
  | "health"
  | "housing"
  | "justice"
  | "communications"
  | "neighborhoods"
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
  banking: { cash:number; balance:number; savings:number; debt:number; creditScore:number; history:Array<{tick:number;transactionType:string;amount:number;balanceAfter:number;label:string;counterpartyId:number|null}> };
  housingSituation: { isHomeless:boolean; homelessSinceTick:number|null; previousHomeId:number|null; foodInsecurityDays:number };
  organizedCrime: { organizationId:number|null; kidnappedUntilTick:number|null; kidnappedByOrganizationId:number|null };
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
  communications: { phoneNumber: string; emailAddress: string; unreadCount: number; messages: CommunicationSummary[]; };
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
    sentences: JudicialSentenceSummary[];
    criminalRecordCount: number;
    probationViolations: number;
    communityServiceMinutes: number;
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
  housing: (HomeSummary & { residents: Array<{id:number;name:string}|null>; households: HouseholdSummary[]; arrears:number; history:HousingRecord[] }) | null;
  healthcare: { beds: number; queue: HealthCaseSummary[]; hospitalized: Array<{ id: number; name: string } | null>; patientsTreatedToday: number; ambulances: VehicleSummary[] } | null;
  justice: { institutionType: "court"; dailyCapacity: number; hearingsToday: number; queue: JudicialCaseSummary[] } | { institutionType: "detention_center"; capacity: number; detained: Array<{ id: number; name: string } | null>; activeSentences: JudicialSentenceSummary[] } | null;
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
export type JudicialCaseStatus = "filed" | "prosecutor_review" | "awaiting_hearing" | "in_hearing" | "decided" | "dismissed";
export type SentenceType = "judicial_warning" | "fine" | "compensation" | "probation" | "community_service" | "restraining_order" | "short_detention" | "long_detention";
export type SentenceStatus = "pending" | "active" | "completed" | "violated";

export interface JudicialSentenceSummary {
  id: number;
  caseId: number;
  citizen: { id: number; name: string } | null;
  type: SentenceType;
  label: string;
  status: SentenceStatus;
  startTick: number;
  endTick: number | null;
  amount: number;
  beneficiary: { id: number; name: string } | null;
  requiredMinutes: number;
  completedMinutes: number;
  violationCount: number;
}

export interface JusticeMetrics {
  complaintsFiled: number;
  casesAwaitingHearing: number;
  hearingsToday: number;
  courtCapacityToday: number;
  courtStaffOnDuty: number;
  activeSentences: number;
  citizensOnProbation: number;
  restrainingOrders: number;
  detainedCitizens: number;
  detentionCapacity: number;
  probationViolationsToday: number;
}

export interface JusticeOverview {
  metrics: JusticeMetrics;
  court: BuildingSummary | null;
  detentionCenter: BuildingSummary | null;
  queue: JudicialCaseSummary[];
  activeSentences: JudicialSentenceSummary[];
}

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
  complaintId: number | null;
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
  prosecutorReviewTick: number | null;
  prosecutorDecision: string | null;
  priority: number;
  delayCount: number;
  sentences: JudicialSentenceSummary[];
  timeline: Array<{ tick: number; eventType: string; label: string; detail: string }>;
  defendantName: string | null;
}

export interface JudicialCaseDetail extends JudicialCaseSummary {
  kind: "case";
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
