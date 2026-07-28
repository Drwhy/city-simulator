from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Activity(StrEnum):
    SLEEPING = "sleeping"
    WORKING = "working"
    WALKING = "walking"
    DRIVING = "driving"
    WAITING_BUS = "waiting_bus"
    RIDING_BUS = "riding_bus"
    EATING = "eating"
    RELAXING = "relaxing"
    AT_HOME = "at_home"
    DETAINED = "detained"
    SHOPPING = "shopping"
    WAITING_MEDICAL = "waiting_medical"
    IN_TREATMENT = "in_treatment"
    HOSPITALIZED = "hospitalized"


class BuildingType(StrEnum):
    HOME = "home"
    OFFICE = "office"
    FACTORY = "factory"
    SHOP = "shop"
    CAFE = "cafe"
    PARK = "park"
    PUBLIC = "public"
    POLICE = "police"
    HOSPITAL = "hospital"


class TransportMode(StrEnum):
    WALK = "walk"
    CAR = "car"
    BUS = "bus"


class TravelStage(StrEnum):
    IDLE = "idle"
    WALKING = "walking"
    TO_BUS_STOP = "to_bus_stop"
    WAITING_BUS = "waiting_bus"
    ON_BUS = "on_bus"
    FROM_BUS_STOP = "from_bus_stop"
    DRIVING = "driving"


class VehicleType(StrEnum):
    CAR = "car"
    BUS = "bus"
    POLICE = "police"
    AMBULANCE = "ambulance"


class VehicleStatus(StrEnum):
    PARKED = "parked"
    DRIVING = "driving"
    IN_SERVICE = "in_service"
    STOPPED = "stopped"
    RESPONDING = "responding"
    ON_SCENE = "on_scene"
    RETURNING = "returning"
    TRANSPORTING = "transporting"


class HealthCondition(StrEnum):
    HEALTHY = "healthy"
    MINOR_INJURY = "minor_injury"
    SERIOUS_INJURY = "serious_injury"
    MILD_ILLNESS = "mild_illness"
    SEVERE_ILLNESS = "severe_illness"
    RECOVERING = "recovering"


class CareStatus(StrEnum):
    NONE = "none"
    WAITING_AMBULANCE = "waiting_ambulance"
    AMBULANCE_DISPATCHED = "ambulance_dispatched"
    IN_AMBULANCE = "in_ambulance"
    WAITING_CONSULTATION = "waiting_consultation"
    IN_CONSULTATION = "in_consultation"
    HOSPITALIZED = "hospitalized"
    RECOVERING = "recovering"


class IncidentStatus(StrEnum):
    ACTIVE = "active"
    REPORTED = "reported"
    RESPONDING = "responding"
    ON_SCENE = "on_scene"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class InvestigationStatus(StrEnum):
    OPEN = "open"
    SUSPECT_IDENTIFIED = "suspect_identified"
    ARRESTED = "arrested"
    REFERRED = "referred"
    CLOSED = "closed"


class JudicialCaseStatus(StrEnum):
    FILED = "filed"
    AWAITING_HEARING = "awaiting_hearing"
    DECIDED = "decided"
    DISMISSED = "dismissed"


class SocialEventType(StrEnum):
    COFFEE = "coffee"
    PARK_MEETUP = "park_meetup"


class SocialEventStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BusinessStatus(StrEnum):
    HEALTHY = "healthy"
    FRAGILE = "fragile"
    DEFICIT = "deficit"
    CLOSED = "closed"


class JobApplicationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


@dataclass(slots=True)
class Needs:
    hunger: float = 10.0
    fatigue: float = 10.0
    stress: float = 5.0
    social: float = 15.0

    def clamp(self) -> None:
        self.hunger = max(0.0, min(100.0, self.hunger))
        self.fatigue = max(0.0, min(100.0, self.fatigue))
        self.stress = max(0.0, min(100.0, self.stress))
        self.social = max(0.0, min(100.0, self.social))


@dataclass(slots=True)
class ConflictRecord:
    tick: int
    level: int
    label: str
    title: str
    incident_id: int | None = None
    building_id: int | None = None
    role: str = "participant"
    outcome: str | None = None


@dataclass(slots=True)
class Relationship:
    other_id: int
    familiarity: float = 0.0
    affection: float = 0.0
    trust: float = 0.0
    positive_interactions: int = 0
    negative_interactions: int = 0
    last_interaction_tick: int = 0
    consecutive_negative_interactions: int = 0
    conflict_score: float = 0.0
    conflict_level: int = 0
    peak_conflict_level: int = 0
    last_conflict_tick: int | None = None
    conflict_history: list[ConflictRecord] = field(default_factory=list)


@dataclass(slots=True)
class Household:
    id: int
    home_id: int
    member_ids: list[int]
    cohesion: float = 50.0
    shared_meals: int = 0
    conflicts: int = 0
    income_today: float = 0.0
    recurring_expenses_today: float = 0.0
    food_expenses_today: float = 0.0
    goods_expenses_today: float = 0.0
    total_income: float = 0.0
    total_expenses: float = 0.0
    debt: float = 0.0
    overdraft_limit: float = 240.0
    financial_stress: float = 10.0
    food_budget_daily: float = 28.0
    goods_budget_daily: float = 12.0
    financial_history: list[HouseholdFinancialRecord] = field(default_factory=list)


@dataclass(slots=True)
class HouseholdFinancialRecord:
    day: int
    income: float
    recurring_expenses: float
    food_expenses: float
    goods_expenses: float
    debt: float
    financial_stress: float


@dataclass(slots=True)
class SocialEvent:
    id: int
    event_type: SocialEventType
    host_id: int
    guest_ids: list[int]
    accepted_ids: list[int]
    declined_ids: list[int]
    building_id: int
    planned_tick: int
    duration_minutes: int = 75
    status: SocialEventStatus = SocialEventStatus.PLANNED
    started_tick: int | None = None
    completed_tick: int | None = None

    @property
    def participant_ids(self) -> list[int]:
        return [self.host_id, *self.accepted_ids]

    @property
    def end_tick(self) -> int:
        return self.planned_tick + self.duration_minutes


@dataclass(slots=True)
class Building:
    id: int
    name: str
    building_type: BuildingType
    x: int
    y: int
    width: int = 2
    height: int = 2
    capacity: int = 10
    occupants: set[int] = field(default_factory=set)
    employees_required: int = 1
    food_stock: float = 0.0
    goods_stock: float = 0.0
    revenue_today: float = 0.0
    cash: float = 0.0
    total_revenue: float = 0.0
    payroll_today: float = 0.0
    fixed_costs_today: float = 0.0
    result_today: float = 0.0
    fixed_cost_daily: float = 0.0
    employee_capacity: int = 0
    target_employees: int = 0
    open_positions: int = 0
    service_level: float = 100.0
    business_status: BusinessStatus = BusinessStatus.HEALTHY
    deficit_days: int = 0
    productive_minutes_today: int = 0
    financial_history: list[BusinessFinancialRecord] = field(default_factory=list)
    employment_events: list[EmploymentRecord] = field(default_factory=list)
    medical_beds: int = 0
    medical_queue: list[int] = field(default_factory=list)
    hospitalized_ids: set[int] = field(default_factory=set)
    patients_treated_today: int = 0
    medical_wait_minutes_today: int = 0

    @property
    def entrance(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height
@dataclass(slots=True)
class BusinessFinancialRecord:
    day: int
    revenue: float
    payroll: float
    fixed_costs: float
    result: float
    cash: float
    service_level: float
    status: BusinessStatus


@dataclass(slots=True)
class EmploymentRecord:
    tick: int
    event_type: str
    label: str
    building_id: int | None
    job_title: str | None
    salary_daily: float
    reason: str


@dataclass(slots=True)
class JobApplication:
    id: int
    citizen_id: int
    building_id: int
    job_title: str
    salary_daily: float
    submitted_tick: int
    score: float
    status: JobApplicationStatus = JobApplicationStatus.PENDING
    resolved_tick: int | None = None
    reason: str | None = None


@dataclass(slots=True)
class BusStop:
    id: int
    name: str
    x: int
    y: int
    line_id: int
    sequence: int

    @property
    def position(self) -> tuple[int, int]:
        return self.x, self.y


@dataclass(slots=True)
class BusLine:
    id: int
    name: str
    stop_ids: list[int]
    route: list[tuple[int, int]]
    fare: float = 2.0


@dataclass(slots=True)
class Vehicle:
    id: int
    vehicle_type: VehicleType
    x: int
    y: int
    capacity: int
    status: VehicleStatus
    owner_id: int | None = None
    line_id: int | None = None
    passenger_ids: set[int] = field(default_factory=set)
    route: list[tuple[int, int]] = field(default_factory=list)
    route_index: int = 0
    target_building_id: int | None = None
    current_building_id: int | None = None
    delay_minutes: int = 0
    distance_today: int = 0
    incident_id: int | None = None
    service_started_tick: int | None = None
    crew_ids: set[int] = field(default_factory=set)
    health_case_id: int | None = None


@dataclass(slots=True)
class PoliceMeasure:
    tick: int
    incident_id: int
    measure_type: str
    label: str
    duration_minutes: int = 0
    reason: str = ""
    officer_ids: tuple[int, ...] = ()


@dataclass(slots=True)
class Citizen:
    id: int
    first_name: str
    last_name: str
    age: int
    home_id: int
    workplace_id: int | None
    job_title: str | None
    salary_daily: float
    x: int
    y: int
    money: float
    activity: Activity = Activity.SLEEPING
    destination_building_id: int | None = None
    planned_activity: Activity = Activity.SLEEPING
    needs: Needs = field(default_factory=Needs)
    relationships: dict[int, Relationship] = field(default_factory=dict)
    last_decision_reason: str = "Initialisation de la simulation"
    minutes_late_today: int = 0

    household_id: int | None = None
    sociability: float = 50.0
    agreeableness: float = 50.0
    spontaneity: float = 50.0
    aggression: float = 25.0
    impulsivity: float = 30.0
    grudge_tendency: float = 30.0
    favorite_place_visits: dict[int, int] = field(default_factory=dict)
    social_event_id: int | None = None
    social_interactions_today: int = 0
    invitations_sent: int = 0
    invitations_accepted: int = 0

    owned_vehicle_id: int | None = None
    transport_mode: TransportMode = TransportMode.WALK
    last_transport_mode: TransportMode = TransportMode.WALK
    travel_stage: TravelStage = TravelStage.IDLE
    route: list[tuple[int, int]] = field(default_factory=list)
    route_index: int = 0
    active_vehicle_id: int | None = None
    origin_stop_id: int | None = None
    destination_stop_id: int | None = None
    waiting_since_tick: int | None = None
    trip_started_tick: int | None = None
    trip_distance: int = 0
    last_trip_minutes: int = 0
    travel_minutes_today: int = 0
    trips_today: int = 0

    health: float = 100.0
    offenses_committed: int = 0
    victimizations: int = 0
    arrests: int = 0
    detained_until_tick: int | None = None
    active_case_ids: list[int] = field(default_factory=list)
    health_condition: HealthCondition = HealthCondition.HEALTHY
    care_status: CareStatus = CareStatus.NONE
    pain: float = 0.0
    injury_severity: float = 0.0
    illness_severity: float = 0.0
    active_health_case_id: int | None = None
    medical_leave_until_tick: int | None = None
    incapacity_until_tick: int | None = None
    hospitalized_until_tick: int | None = None
    health_history: list[MedicalRecord] = field(default_factory=list)

    # Emploi persistant et suivi des shifts.
    work_start_hour: int = 8
    work_end_hour: int = 17
    work_days: tuple[int, ...] = (1, 2, 3, 4, 5)
    minutes_worked_today: int = 0
    shifts_completed: int = 0
    missed_shifts: int = 0
    job_performance: float = 65.0
    job_satisfaction: float = 55.0
    last_paid_day: int = 0
    employed_since_tick: int = 0
    job_search_active: bool = False
    job_search_since_tick: int | None = None
    last_job_change_tick: int = 0
    application_ids: list[int] = field(default_factory=list)
    employment_history: list[EmploymentRecord] = field(default_factory=list)
    experience_by_job: dict[str, float] = field(default_factory=dict)
    income_today: float = 0.0
    expenses_today: float = 0.0
    financial_stress: float = 10.0
    overdraft_limit: float = 120.0


    # Consommation simple du foyer.
    food_units: float = 5.0
    goods_units: float = 2.0
    last_shopping_tick: int | None = None
    last_meal_tick: int | None = None
    shopping_visits: int = 0
    intoxication: float = 0.0

    # Police et consÃ©quences immÃ©diates.
    police_history: list[PoliceMeasure] = field(default_factory=list)
    current_detention_type: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass(slots=True)
class Incident:
    id: int
    incident_type: str
    title: str
    description: str
    severity: str
    citizen_ids: tuple[int, ...]
    offender_id: int | None
    victim_ids: tuple[int, ...]
    witness_ids: tuple[int, ...]
    building_id: int | None
    vehicle_id: int | None
    x: int
    y: int
    created_tick: int
    expires_tick: int
    status: IncidentStatus = IncidentStatus.ACTIVE
    reported: bool = False
    police_vehicle_id: int | None = None
    dispatched_tick: int | None = None
    police_arrival_tick: int | None = None
    resolved_tick: int | None = None
    resolution: str | None = None
    conflict_level: int = 0
    investigation_id: int | None = None
    police_action: str | None = None
    police_officer_ids: tuple[int, ...] = ()
    detained_ids: tuple[int, ...] = ()
    health_case_ids: tuple[int, ...] = ()


@dataclass(slots=True)
class MedicalRecord:
    tick: int
    event_type: str
    label: str
    severity: float
    source: str
    incident_id: int | None = None
    hospital_id: int | None = None
    incapacity_minutes: int = 0


@dataclass(slots=True)
class HealthCase:
    id: int
    citizen_id: int
    source: str
    severity: float
    created_tick: int
    status: CareStatus
    hospital_id: int | None = None
    ambulance_id: int | None = None
    incident_id: int | None = None
    queued_tick: int | None = None
    consultation_started_tick: int | None = None
    completed_tick: int | None = None
    transport_required: bool = False
    medical_report_created: bool = False


@dataclass(slots=True)
class Evidence:
    id: int
    investigation_id: int
    evidence_type: str
    description: str
    reliability: float
    citizen_id: int | None = None
    created_tick: int = 0


@dataclass(slots=True)
class Investigation:
    id: int
    incident_id: int
    status: InvestigationStatus
    opened_tick: int
    updated_tick: int
    suspect_ids: list[int] = field(default_factory=list)
    lead_suspect_id: int | None = None
    evidence_ids: list[int] = field(default_factory=list)
    confidence: float = 0.0
    arrest_tick: int | None = None
    case_id: int | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class JudicialCase:
    id: int
    investigation_id: int
    incident_id: int
    defendant_id: int
    charges: list[str]
    status: JudicialCaseStatus
    filed_tick: int
    hearing_tick: int
    evidence_score: float
    decided_tick: int | None = None
    verdict: str | None = None
    sentence: str | None = None


@dataclass(slots=True)
class DomainEvent:
    id: int
    tick: int
    day: int
    hour: int
    minute: int
    event_type: str
    message: str
    citizen_ids: tuple[int, ...] = ()
    building_id: int | None = None
    vehicle_id: int | None = None
    severity: str = "info"
    incident_id: int | None = None
