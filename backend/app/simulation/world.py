from __future__ import annotations

import random
from collections import Counter
from typing import Any

from .economy import (
    assigned_staff_count,
    close_economic_day,
    economy_overview,
    initialize_economy,
    is_employer,
    update_economy,
)

from .generator import generate_buildings, generate_citizens, generate_households, generate_vehicles
from .models import (
    Activity,
    Building,
    BusinessFinancialRecord,
    BusinessStatus,
    EmploymentRecord,
    HouseholdFinancialRecord,
    JobApplication,
    JobApplicationStatus,
    BuildingType,
    BusLine,
    BusStop,
    Citizen,
    ConflictRecord,
    DomainEvent,
    Evidence,
    Household,
    Incident,
    IncidentStatus,
    Investigation,
    InvestigationStatus,
    JudicialCase,
    JudicialCaseStatus,
    Needs,
    PoliceMeasure,
    Relationship,
    SocialEvent,
    SocialEventStatus,
    SocialEventType,
    TransportMode,
    TravelStage,
    Vehicle,
    VehicleStatus,
    VehicleType,
)
from .social import (
    conflict_label,
    conflict_propensity,
    cool_down_conflicts,
    relationship_label,
    temperament_label,
    resolve_ambient_social_life,
    resolve_household_life,
    social_commitment,
    update_social_calendar,
)
from .snapshot import build_dynamic_snapshot
from .work import (
    apply_police_measure,
    building_operational,
    is_on_duty,
    needs_shopping,
    refresh_police_crews,
    shift_active,
    shift_commute_window,
    staff_count,
    update_work_and_consumption,
    weekday,
)
from .transport import (
    MAP_HEIGHT,
    MAP_WIDTH,
    forward_route_distance,
    generate_bus_network,
    generate_road_cells,
    manhattan_path,
    road_path,
)


class World:
    MAP_WIDTH = MAP_WIDTH
    MAP_HEIGHT = MAP_HEIGHT
    BUS_SPEED = 2
    CAR_SPEED = 2
    BUS_START_HOUR = 6
    BUS_END_HOUR = 23
    BUS_MAX_WAIT_MINUTES = 20

    def __init__(self, *, seed: int = 12345, citizen_count: int = 100) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.tick = 0
        self.day = 1
        self.hour = 6
        self.minute = 0

        self.road_cells = generate_road_cells()
        self.bus_stops, self.bus_lines = generate_bus_network(self.road_cells)
        self._stops_by_position = {stop.position: stop for stop in self.bus_stops.values()}

        self.buildings: dict[int, Building] = generate_buildings()
        self.citizens: dict[int, Citizen] = generate_citizens(
            self.buildings,
            count=citizen_count,
            seed=seed,
        )
        self.households: dict[int, Household] = generate_households(
            self.citizens,
            self.buildings,
            seed=seed,
        )
        self.social_events: dict[int, SocialEvent] = {}
        self._next_social_event_id = 1
        self.vehicles: dict[int, Vehicle] = generate_vehicles(
            self.citizens,
            self.buildings,
            self.bus_lines[1].route,
            seed=seed,
        )

        self.events: list[DomainEvent] = []
        self.incidents: dict[int, Incident] = {}
        self.evidence: dict[int, Evidence] = {}
        self.investigations: dict[int, Investigation] = {}
        self.judicial_cases: dict[int, JudicialCase] = {}
        self._next_event_id = 1
        self._next_incident_id = 1
        self._next_evidence_id = 1
        self._next_investigation_id = 1
        self._next_case_id = 1
        self._last_social_slot = -1
        self._last_social_planning_day = 0
        self._last_household_slot = -1
        self._last_incident_hour = -1
        self._last_traffic_event_hour = -1
        self._last_justice_hour = -1
        self.trip_counts_today: Counter[str] = Counter({mode.value: 0 for mode in TransportMode})
        self.bus_boardings_today = 0
        self.traffic_delay_today = 0
        self.social_invitations_today = 0
        self.social_acceptances_today = 0
        self.social_gatherings_completed = 0
        self.police_responses_today = 0
        self.police_response_minutes_today = 0
        self.arrests_today = 0
        self.cases_filed_today = 0
        self.shop_sales_today = 0.0
        self.shopping_trips_today = 0
        self.police_warnings_today = 0
        self.police_detentions_today = 0
        self.job_applications: dict[int, JobApplication] = {}
        self._next_job_application_id = 1
        self._last_labor_market_day = 0
        self.hires_today = 0
        self.layoffs_today = 0
        self.resignations_today = 0
        self.public_spending_total = 0.0
        initialize_economy(self)
        self._emit("simulation_started", "La ville commence une nouvelle journée.")

    @property
    def total_minutes(self) -> int:
        return ((self.day - 1) * 24 * 60) + self.hour * 60 + self.minute

    @property
    def simulation_time_label(self) -> str:
        return f"Jour {self.day} — {self.hour:02d}:{self.minute:02d}"

    @property
    def bus_operating(self) -> bool:
        return self.BUS_START_HOUR <= self.hour < self.BUS_END_HOUR

    def advance_one_minute(self) -> None:
        self.tick += 1
        self.minute += 1
        if self.minute >= 60:
            self.minute = 0
            self.hour += 1
        if self.hour >= 24:
            self.hour = 0
            self.day += 1
            self._reset_daily_counters()
            self._emit("new_day", f"Le jour {self.day} commence.")

        self._update_needs()
        update_economy(self)
        update_social_calendar(self)
        self._plan_activities()
        self._move_walkers()
        self._move_buses()
        self._move_police_units()
        self._move_cars()
        self._resolve_activities()
        update_work_and_consumption(self)
        self._resolve_social_life()
        resolve_household_life(self)
        self._resolve_incidents()
        self._dispatch_police()
        self._advance_justice()
        self._expire_incidents()
        self._report_traffic_if_needed()

    def run_minutes(self, minutes: int) -> None:
        for _ in range(minutes):
            self.advance_one_minute()

    def _reset_daily_counters(self) -> None:
        self.trip_counts_today = Counter({mode.value: 0 for mode in TransportMode})
        self.hires_today = 0
        self.layoffs_today = 0
        self.resignations_today = 0
        close_economic_day(self, self.day - 1)
        self.bus_boardings_today = 0
        self.traffic_delay_today = 0
        self.social_invitations_today = 0
        self.social_acceptances_today = 0
        self.social_gatherings_completed = 0
        self.police_responses_today = 0
        self.police_response_minutes_today = 0
        self.arrests_today = 0
        self.cases_filed_today = 0
        self.shop_sales_today = 0.0
        self.shopping_trips_today = 0
        self.police_warnings_today = 0
        self.police_detentions_today = 0
        cool_down_conflicts(self)
        for citizen in self.citizens.values():
            citizen.minutes_late_today = 0
            citizen.travel_minutes_today = 0
            citizen.trips_today = 0
            citizen.social_interactions_today = 0
            citizen.minutes_worked_today = 0
            citizen.health = min(100.0, citizen.health + 2.0)
        for vehicle in self.vehicles.values():
            vehicle.delay_minutes = 0
            vehicle.distance_today = 0
        for building in self.buildings.values():
            building.revenue_today = 0.0
            if building.building_type == BuildingType.SHOP:
                building.food_stock = min(500.0, building.food_stock + 110.0)
                building.goods_stock = min(260.0, building.goods_stock + 45.0)

    def _update_needs(self) -> None:
        for citizen in self.citizens.values():
            if citizen.activity == Activity.SLEEPING:
                citizen.needs.fatigue -= 0.18
                citizen.needs.hunger += 0.025
                citizen.needs.stress -= 0.025
            elif citizen.activity == Activity.EATING:
                citizen.needs.hunger -= 0.5
                citizen.needs.fatigue += 0.02
            elif citizen.activity == Activity.RELAXING:
                citizen.needs.stress -= 0.08
                citizen.needs.social -= 0.035
                citizen.needs.fatigue += 0.015
                citizen.needs.hunger += 0.035
            elif citizen.activity == Activity.WORKING:
                citizen.needs.hunger += 0.05
                citizen.needs.fatigue += 0.045
                citizen.needs.stress += 0.02
                citizen.needs.social += 0.02
            elif citizen.activity == Activity.WAITING_BUS:
                citizen.needs.hunger += 0.04
                citizen.needs.fatigue += 0.02
                citizen.needs.stress += 0.035
            elif citizen.activity in {Activity.DRIVING, Activity.RIDING_BUS}:
                citizen.needs.hunger += 0.035
                citizen.needs.fatigue += 0.025
                citizen.needs.stress += 0.012
            elif citizen.activity == Activity.SHOPPING:
                citizen.needs.hunger += 0.025
                citizen.needs.fatigue += 0.018
                citizen.needs.stress -= 0.008
            elif citizen.activity == Activity.AT_HOME:
                citizen.needs.hunger += 0.035
                citizen.needs.fatigue += 0.02
                citizen.needs.stress -= 0.012
                citizen.needs.social += 0.012
            elif citizen.activity == Activity.DETAINED:
                citizen.needs.hunger += 0.035
                citizen.needs.fatigue += 0.02
                citizen.needs.stress += 0.028
                citizen.needs.social += 0.018
            else:
                citizen.needs.hunger += 0.04
                citizen.needs.fatigue += 0.03
                citizen.needs.social += 0.02
            citizen.needs.clamp()

    def _plan_activities(self) -> None:
        cafe = self._first_building(BuildingType.CAFE)
        park = self._first_building(BuildingType.PARK)
        market = self._first_building(BuildingType.SHOP)

        for citizen in self.citizens.values():
            # Les policiers engagés dans une intervention suivent leur équipage, pas le planificateur civil.
            if citizen.active_vehicle_id is not None:
                active_vehicle = self.vehicles.get(citizen.active_vehicle_id)
                if (
                    active_vehicle is not None
                    and active_vehicle.vehicle_type == VehicleType.POLICE
                    and active_vehicle.status != VehicleStatus.PARKED
                ):
                    continue

            target_id: int
            planned: Activity
            reason: str

            if citizen.detained_until_tick is not None and self.tick < citizen.detained_until_tick:
                station = self._first_building(BuildingType.POLICE)
                target_id = station.id if station is not None else citizen.home_id
                planned = Activity.DETAINED
                detention_label = {
                    "temporary_cell": "mise en cellule",
                    "sobering_cell": "cellule de dégrisement",
                    "custody": "garde à vue",
                }.get(citizen.current_detention_type, "rétention")
                reason = f"La personne fait l'objet d'une {detention_label}."
            else:
                if citizen.detained_until_tick is not None:
                    citizen.detained_until_tick = None
                    citizen.current_detention_type = None

                if self.hour < 6 or self.hour >= 23:
                    target_id = citizen.home_id
                    planned = Activity.SLEEPING
                    reason = "Il est temps de dormir."
                elif citizen.needs.fatigue >= 88:
                    target_id = citizen.home_id
                    planned = Activity.SLEEPING
                    reason = "La fatigue est devenue prioritaire."
                elif shift_commute_window(self, citizen):
                    target_id = citizen.workplace_id or citizen.home_id
                    planned = Activity.WORKING
                    reason = (
                        f"Shift prévu de {citizen.work_start_hour:02d}:00 à "
                        f"{citizen.work_end_hour:02d}:00."
                    )
                elif citizen.needs.hunger >= 52 and citizen.food_units >= 0.75:
                    target_id = citizen.home_id
                    planned = Activity.EATING
                    reason = "Un repas peut être préparé avec les provisions disponibles."
                elif (
                    market is not None
                    and needs_shopping(citizen)
                    and 7 <= self.hour < 20
                    and citizen.money >= 6
                ):
                    target_id = market.id
                    planned = Activity.SHOPPING
                    reason = "Les réserves de nourriture ou de biens courants sont faibles."
                elif (
                    citizen.needs.hunger >= 75
                    and cafe is not None
                    and citizen.money >= 8
                    and building_operational(self, cafe.id)
                ):
                    target_id = cafe.id
                    planned = Activity.EATING
                    reason = "La faim est devenue prioritaire et le café est ouvert."
                else:
                    commitment = social_commitment(self, citizen)
                    if commitment is not None:
                        target_id = commitment.building_id
                        planned = Activity.RELAXING
                        building = self.buildings[target_id]
                        reason = f"Une rencontre sociale est prévue à {building.name}."
                    elif 17 <= self.hour < 22 and citizen.needs.social >= 55 and park is not None:
                        target_id = park.id
                        planned = Activity.RELAXING
                        reason = "Le besoin social motive une sortie au parc."
                    else:
                        target_id = citizen.home_id
                        planned = Activity.AT_HOME
                        reason = "Aucune obligation urgente : retour au domicile."

            target = self.buildings[target_id]
            trip_is_missing = (
                citizen.travel_stage == TravelStage.IDLE
                and (citizen.x, citizen.y) != target.entrance
            )
            if (
                citizen.destination_building_id != target_id
                or citizen.planned_activity != planned
                or trip_is_missing
            ):
                self._set_destination(citizen, target_id, planned, reason)

    def _set_destination(
        self,
        citizen: Citizen,
        target_id: int,
        planned: Activity,
        reason: str,
    ) -> None:
        self._cancel_active_trip(citizen)
        citizen.destination_building_id = target_id
        citizen.planned_activity = planned
        destination = self.buildings[target_id]

        if (citizen.x, citizen.y) == destination.entrance:
            destination.occupants.add(citizen.id)
            citizen.activity = planned
            citizen.travel_stage = TravelStage.IDLE
            citizen.last_decision_reason = reason
            return

        self._begin_trip(citizen, destination, reason)

    def _cancel_active_trip(self, citizen: Citizen) -> None:
        if citizen.active_vehicle_id is not None:
            vehicle = self.vehicles.get(citizen.active_vehicle_id)
            if vehicle is not None:
                vehicle.passenger_ids.discard(citizen.id)
                if vehicle.vehicle_type == VehicleType.CAR:
                    vehicle.status = VehicleStatus.PARKED
                    vehicle.route = []
                    vehicle.route_index = 0
                    vehicle.target_building_id = None
                    vehicle.current_building_id = None
        citizen.active_vehicle_id = None
        citizen.origin_stop_id = None
        citizen.destination_stop_id = None
        citizen.waiting_since_tick = None
        citizen.route = []
        citizen.route_index = 0
        citizen.travel_stage = TravelStage.IDLE

    def _begin_trip(self, citizen: Citizen, destination: Building, reason: str) -> None:
        self._remove_from_all_buildings(citizen.id)
        start = (citizen.x, citizen.y)
        end = destination.entrance
        direct_distance = abs(end[0] - start[0]) + abs(end[1] - start[1])
        citizen.trip_started_tick = self.tick
        citizen.trip_distance = 0
        citizen.trips_today += 1

        car = self.vehicles.get(citizen.owned_vehicle_id) if citizen.owned_vehicle_id else None
        car_available = bool(
            car
            and car.status == VehicleStatus.PARKED
            and (car.x, car.y) == start
            and direct_distance >= 6
        )
        bus_plan = self._best_bus_trip(start, end, direct_distance)

        if direct_distance <= 5:
            mode = TransportMode.WALK
        elif car_available:
            mode = TransportMode.CAR
        elif bus_plan is not None and citizen.money >= self.bus_lines[1].fare:
            mode = TransportMode.BUS
        else:
            mode = TransportMode.WALK

        citizen.transport_mode = mode
        self.trip_counts_today[mode.value] += 1

        if mode == TransportMode.CAR and car is not None:
            car.route = road_path(start, end, self.road_cells)
            car.route_index = 0
            car.target_building_id = destination.id
            car.current_building_id = None
            car.status = VehicleStatus.DRIVING
            car.passenger_ids = {citizen.id}
            citizen.active_vehicle_id = car.id
            citizen.travel_stage = TravelStage.DRIVING
            citizen.activity = Activity.DRIVING
            citizen.last_decision_reason = f"{reason} La voiture est choisie pour réduire le temps de trajet."
            return

        if mode == TransportMode.BUS and bus_plan is not None:
            origin_stop, destination_stop = bus_plan
            citizen.origin_stop_id = origin_stop.id
            citizen.destination_stop_id = destination_stop.id
            citizen.route = manhattan_path(start, origin_stop.position)
            citizen.route_index = 0
            citizen.travel_stage = TravelStage.TO_BUS_STOP
            citizen.activity = Activity.WALKING
            citizen.last_decision_reason = (
                f"{reason} Le bus est choisi : arrêt {origin_stop.name}, "
                f"puis {destination_stop.name}."
            )
            if not citizen.route:
                citizen.travel_stage = TravelStage.WAITING_BUS
                citizen.activity = Activity.WAITING_BUS
                citizen.waiting_since_tick = self.tick
            return

        citizen.route = manhattan_path(start, end, horizontal_first=(citizen.id % 2 == 0))
        citizen.route_index = 0
        citizen.travel_stage = TravelStage.WALKING
        citizen.activity = Activity.WALKING
        citizen.last_decision_reason = f"{reason} La marche est le mode le plus simple pour ce trajet."

    def _best_bus_trip(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        direct_distance: int,
    ) -> tuple[BusStop, BusStop] | None:
        if not self.bus_operating or direct_distance < 7:
            return None
        line = self.bus_lines[1]
        origins = sorted(
            self.bus_stops.values(),
            key=lambda stop: abs(stop.x - start[0]) + abs(stop.y - start[1]),
        )[:3]
        destinations = sorted(
            self.bus_stops.values(),
            key=lambda stop: abs(stop.x - end[0]) + abs(stop.y - end[1]),
        )[:3]

        best: tuple[float, BusStop, BusStop] | None = None
        for origin in origins:
            for destination in destinations:
                if origin.id == destination.id:
                    continue
                walk_to = abs(origin.x - start[0]) + abs(origin.y - start[1])
                walk_from = abs(destination.x - end[0]) + abs(destination.y - end[1])
                if walk_to > 9 or walk_from > 9:
                    continue
                ride = forward_route_distance(line.route, origin.position, destination.position)
                generalized_cost = walk_to + walk_from + ride / self.BUS_SPEED + 4
                candidate = (generalized_cost, origin, destination)
                if best is None or candidate[0] < best[0]:
                    best = candidate

        if best is None or best[0] > direct_distance * 1.35:
            return None
        return best[1], best[2]

    def _move_walkers(self) -> None:
        for citizen in self.citizens.values():
            if citizen.travel_stage == TravelStage.WAITING_BUS:
                waited = self.tick - (citizen.waiting_since_tick or self.tick)
                if waited >= self.BUS_MAX_WAIT_MINUTES:
                    self._fallback_to_walking(citizen)
                continue
            if citizen.travel_stage not in {
                TravelStage.WALKING,
                TravelStage.TO_BUS_STOP,
                TravelStage.FROM_BUS_STOP,
            }:
                continue

            if citizen.route_index < len(citizen.route):
                citizen.x, citizen.y = citizen.route[citizen.route_index]
                citizen.route_index += 1
                citizen.trip_distance += 1

            if citizen.route_index < len(citizen.route):
                continue

            if citizen.travel_stage == TravelStage.TO_BUS_STOP:
                citizen.travel_stage = TravelStage.WAITING_BUS
                citizen.activity = Activity.WAITING_BUS
                citizen.waiting_since_tick = self.tick
            else:
                self._finish_trip(citizen)

    def _fallback_to_walking(self, citizen: Citizen) -> None:
        destination = self.buildings.get(citizen.destination_building_id)
        if destination is None:
            return
        citizen.transport_mode = TransportMode.WALK
        citizen.origin_stop_id = None
        citizen.destination_stop_id = None
        citizen.waiting_since_tick = None
        citizen.route = manhattan_path((citizen.x, citizen.y), destination.entrance)
        citizen.route_index = 0
        citizen.travel_stage = TravelStage.WALKING
        citizen.activity = Activity.WALKING
        citizen.needs.stress = min(100.0, citizen.needs.stress + 2.0)
        self._emit(
            "bus_wait_abandoned",
            f"{citizen.full_name} renonce au bus après une attente trop longue.",
            citizen_ids=(citizen.id,),
            severity="warning",
        )

    def _move_buses(self) -> None:
        occupancy = self._moving_vehicle_occupancy()
        for bus in self.vehicles.values():
            if bus.vehicle_type != VehicleType.BUS:
                continue
            if not self.bus_operating:
                bus.status = VehicleStatus.STOPPED
                continue

            bus.status = VehicleStatus.IN_SERVICE
            stop = self._stops_by_position.get((bus.x, bus.y))
            if stop is not None:
                self._service_bus_stop(bus, stop)

            for _ in range(self.BUS_SPEED):
                if not bus.route:
                    break
                next_index = (bus.route_index + 1) % len(bus.route)
                next_cell = bus.route[next_index]
                if self._vehicle_delayed(bus, next_cell, occupancy):
                    break
                occupancy[(bus.x, bus.y)] -= 1
                bus.route_index = next_index
                bus.x, bus.y = next_cell
                bus.distance_today += 1
                occupancy[next_cell] += 1
                for citizen_id in sorted(bus.passenger_ids):
                    passenger = self.citizens[citizen_id]
                    passenger.x, passenger.y = next_cell
                    passenger.trip_distance += 1
                stop = self._stops_by_position.get(next_cell)
                if stop is not None:
                    self._service_bus_stop(bus, stop)
                    break

    def _service_bus_stop(self, bus: Vehicle, stop: BusStop) -> None:
        for citizen_id in sorted(tuple(bus.passenger_ids)):
            citizen = self.citizens[citizen_id]
            if citizen.destination_stop_id != stop.id:
                continue
            bus.passenger_ids.discard(citizen.id)
            citizen.active_vehicle_id = None
            citizen.x, citizen.y = stop.position
            destination = self.buildings.get(citizen.destination_building_id)
            if destination is None:
                continue
            citizen.route = manhattan_path(stop.position, destination.entrance)
            citizen.route_index = 0
            citizen.travel_stage = TravelStage.FROM_BUS_STOP
            citizen.activity = Activity.WALKING
            if not citizen.route:
                self._finish_trip(citizen)

        waiting = sorted(
            citizen.id
            for citizen in self.citizens.values()
            if citizen.travel_stage == TravelStage.WAITING_BUS
            and citizen.origin_stop_id == stop.id
            and (citizen.x, citizen.y) == stop.position
        )
        line = self.bus_lines[bus.line_id or 1]
        for citizen_id in waiting:
            if len(bus.passenger_ids) >= bus.capacity:
                break
            citizen = self.citizens[citizen_id]
            if citizen.money < line.fare:
                self._fallback_to_walking(citizen)
                continue
            citizen.money = round(citizen.money - line.fare, 2)
            citizen.active_vehicle_id = bus.id
            citizen.travel_stage = TravelStage.ON_BUS
            citizen.activity = Activity.RIDING_BUS
            citizen.waiting_since_tick = None
            bus.passenger_ids.add(citizen.id)
            self.bus_boardings_today += 1
            if self.rng.random() < 0.04:
                self._emit(
                    "bus_boarded",
                    f"{citizen.full_name} monte dans le bus {bus.id} à l'arrêt {stop.name}.",
                    citizen_ids=(citizen.id,),
                    vehicle_id=bus.id,
                )

    def _sync_police_crew(self, unit: Vehicle) -> None:
        station = self._first_building(BuildingType.POLICE)
        for officer_id in tuple(unit.crew_ids):
            officer = self.citizens.get(officer_id)
            if officer is None:
                unit.crew_ids.discard(officer_id)
                continue
            officer.x, officer.y = unit.x, unit.y
            if unit.status == VehicleStatus.PARKED:
                officer.active_vehicle_id = None
                officer.travel_stage = TravelStage.IDLE
                if station is not None:
                    officer.destination_building_id = station.id
                    officer.planned_activity = Activity.WORKING
                    officer.activity = Activity.WORKING if shift_active(self, officer) else Activity.AT_HOME
                    station.occupants.add(officer.id)
            else:
                self._remove_from_all_buildings(officer.id)
                officer.active_vehicle_id = unit.id
                officer.travel_stage = TravelStage.DRIVING
                officer.activity = Activity.DRIVING
                officer.last_decision_reason = f"Intervention de police à bord de l'unité #{unit.id}."

    def _release_police_crew(self, unit: Vehicle) -> None:
        self._sync_police_crew(unit)
        for officer_id in tuple(unit.crew_ids):
            officer = self.citizens.get(officer_id)
            if officer is None:
                continue
            officer.active_vehicle_id = None
            officer.travel_stage = TravelStage.IDLE
        unit.passenger_ids.clear()
        # L'équipage reste affecté tant que les agents sont en service ; il sera recalculé au prochain dispatch.

    def _move_police_units(self) -> None:
        occupancy = self._moving_vehicle_occupancy()
        station = self._first_building(BuildingType.POLICE)
        for unit in self.vehicles.values():
            if unit.vehicle_type != VehicleType.POLICE:
                continue

            if unit.status in {VehicleStatus.RESPONDING, VehicleStatus.RETURNING}:
                for _ in range(self.CAR_SPEED + 1):
                    if unit.route_index >= len(unit.route):
                        break
                    next_cell = unit.route[unit.route_index]
                    if self._vehicle_delayed(unit, next_cell, occupancy):
                        break
                    occupancy[(unit.x, unit.y)] -= 1
                    unit.x, unit.y = next_cell
                    unit.route_index += 1
                    unit.distance_today += 1
                    occupancy[next_cell] += 1

                self._sync_police_crew(unit)
                if unit.route_index < len(unit.route):
                    continue

                if unit.status == VehicleStatus.RESPONDING and unit.incident_id is not None:
                    incident = self.incidents.get(unit.incident_id)
                    if incident is None or incident.status == IncidentStatus.EXPIRED:
                        self._send_police_home(unit)
                        continue
                    unit.status = VehicleStatus.ON_SCENE
                    unit.service_started_tick = self.tick
                    incident.status = IncidentStatus.ON_SCENE
                    incident.police_arrival_tick = self.tick
                    response_minutes = max(0, self.tick - (incident.dispatched_tick or self.tick))
                    self.police_response_minutes_today += response_minutes
                    self._emit(
                        "police_arrived",
                        f"Une unité de police arrive sur l'incident « {incident.title} ».",
                        citizen_ids=incident.citizen_ids,
                        building_id=incident.building_id,
                        vehicle_id=unit.id,
                        severity="warning",
                        incident_id=incident.id,
                    )
                elif unit.status == VehicleStatus.RETURNING:
                    unit.status = VehicleStatus.PARKED
                    unit.route = []
                    unit.route_index = 0
                    unit.current_building_id = station.id if station else None
                    unit.incident_id = None
                    unit.service_started_tick = None
                    self._release_police_crew(unit)

            elif unit.status == VehicleStatus.ON_SCENE and unit.incident_id is not None:
                self._sync_police_crew(unit)
                incident = self.incidents.get(unit.incident_id)
                if incident is None:
                    self._send_police_home(unit)
                    continue
                duration = 12 + incident.conflict_level * 6 + (8 if incident.severity == "danger" else 0)
                if self.tick - (unit.service_started_tick or self.tick) < duration:
                    continue
                self._resolve_police_incident(incident, unit)

    def _send_police_home(self, unit: Vehicle) -> None:
        station = self._first_building(BuildingType.POLICE)
        if station is None:
            unit.status = VehicleStatus.PARKED
            unit.incident_id = None
            return
        unit.status = VehicleStatus.RETURNING
        unit.route = road_path((unit.x, unit.y), station.entrance, self.road_cells)
        unit.route_index = 0
        unit.target_building_id = station.id
        unit.service_started_tick = self.tick
        if not unit.route:
            unit.x, unit.y = station.entrance
            unit.status = VehicleStatus.PARKED
            unit.current_building_id = station.id
            unit.incident_id = None
            self._release_police_crew(unit)

    def _resolve_police_incident(self, incident: Incident, unit: Vehicle) -> None:
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_tick = self.tick
        incident.expires_tick = self.tick + 120
        officer_ids = tuple(sorted(unit.crew_ids))
        incident.police_officer_ids = officer_ids

        offender = self.citizens.get(incident.offender_id or -1)
        measure_label: str | None = None
        detained_ids: tuple[int, ...] = ()
        if offender is not None:
            if incident.incident_type == "serious_assault":
                measure_type, duration = "custody", 8 * 60
                reason = "violences graves nécessitant une garde à vue"
            elif incident.incident_type == "assault":
                measure_type, duration = "custody", 4 * 60
                reason = "violences volontaires constatées"
            elif incident.incident_type == "fight":
                if offender.intoxication >= 35:
                    measure_type, duration = "sobering_cell", self.rng.randint(180, 360)
                    reason = "état d'ivresse et comportement violent"
                else:
                    measure_type, duration = "temporary_cell", self.rng.randint(90, 180)
                    reason = "bagarre et risque de reprise immédiate"
            elif incident.incident_type == "theft":
                measure_type, duration = "temporary_cell", self.rng.randint(90, 180)
                reason = "vérification d'identité et faits de vol"
            elif incident.incident_type == "heated_dispute" and (
                offender.intoxication >= 45 or offender.aggression + offender.impulsivity >= 145
            ):
                measure_type, duration = (
                    ("sobering_cell", self.rng.randint(120, 300))
                    if offender.intoxication >= 45
                    else ("temporary_cell", self.rng.randint(45, 100))
                )
                reason = "trouble persistant malgré les injonctions des agents"
            else:
                measure_type, duration = "warning", 0
                reason = "cessation du trouble et rappel des obligations légales"

            measure = apply_police_measure(
                self,
                offender,
                incident.id,
                measure_type,
                duration,
                reason,
                officer_ids,
            )
            measure_label = measure.label
            incident.police_action = measure.label
            if duration > 0:
                detained_ids = (offender.id,)
                incident.detained_ids = detained_ids
                self.police_detentions_today += 1
            else:
                self.police_warnings_today += 1

        serious = incident.incident_type in {
            "fight", "assault", "serious_assault", "theft"
        }
        investigation = self._open_investigation(incident) if serious else None
        if investigation is None:
            if measure_label is not None:
                incident.resolution = f"La situation est maîtrisée. Mesure prise : {measure_label}."
            else:
                incident.resolution = "La situation est maîtrisée et les personnes présentes sont entendues."
        elif investigation.arrest_tick is not None:
            suspect = self.citizens.get(investigation.lead_suspect_id or -1)
            incident.resolution = (
                f"{suspect.full_name} est placé en garde à vue et un dossier judiciaire est ouvert."
                if suspect else "Une arrestation est effectuée et un dossier judiciaire est ouvert."
            )
        elif investigation.status == InvestigationStatus.SUSPECT_IDENTIFIED:
            suspect = self.citizens.get(investigation.lead_suspect_id or -1)
            suffix = f" Mesure immédiate : {measure_label}." if measure_label else ""
            incident.resolution = (
                f"Une enquête est ouverte ; {suspect.full_name} est identifié comme suspect principal.{suffix}"
                if suspect else f"Une enquête est ouverte avec un suspect principal.{suffix}"
            )
        else:
            suffix = f" Mesure immédiate : {measure_label}." if measure_label else ""
            incident.resolution = (
                "Une enquête est ouverte ; les éléments disponibles restent insuffisants pour une arrestation."
                + suffix
            )

        self._update_conflict_outcome(incident, incident.resolution or "Intervention policière terminée.")
        self.police_responses_today += 1
        self._emit(
            "police_incident_resolved",
            f"La police clôt l'intervention : {incident.resolution}",
            citizen_ids=tuple(dict.fromkeys((*incident.citizen_ids, *officer_ids, *detained_ids))),
            building_id=incident.building_id,
            vehicle_id=unit.id,
            severity="info",
            incident_id=incident.id,
        )
        self._send_police_home(unit)

    def _add_evidence(
        self,
        investigation: Investigation,
        evidence_type: str,
        description: str,
        reliability: float,
        *,
        citizen_id: int | None = None,
    ) -> Evidence:
        evidence = Evidence(
            id=self._next_evidence_id,
            investigation_id=investigation.id,
            evidence_type=evidence_type,
            description=description,
            reliability=max(0.0, min(1.0, reliability)),
            citizen_id=citizen_id,
            created_tick=self.tick,
        )
        self._next_evidence_id += 1
        self.evidence[evidence.id] = evidence
        investigation.evidence_ids.append(evidence.id)
        investigation.updated_tick = self.tick
        return evidence

    def _investigation_confidence(self, investigation: Investigation) -> float:
        rows = [self.evidence[evidence_id] for evidence_id in investigation.evidence_ids if evidence_id in self.evidence]
        if not rows:
            return 0.0
        reliability_sum = sum(item.reliability for item in rows)
        diversity = len({item.evidence_type for item in rows})
        return min(100.0, reliability_sum * 24.0 + diversity * 7.0)

    def _open_investigation(self, incident: Incident) -> Investigation:
        if incident.investigation_id is not None and incident.investigation_id in self.investigations:
            return self.investigations[incident.investigation_id]

        investigation = Investigation(
            id=self._next_investigation_id,
            incident_id=incident.id,
            status=InvestigationStatus.OPEN,
            opened_tick=self.tick,
            updated_tick=self.tick,
        )
        self._next_investigation_id += 1
        self.investigations[investigation.id] = investigation
        incident.investigation_id = investigation.id

        for witness_id in incident.witness_ids[:4]:
            witness = self.citizens.get(witness_id)
            if witness is None:
                continue
            reliability = self.rng.uniform(0.48, 0.86)
            self._add_evidence(
                investigation,
                "witness_statement",
                f"Témoignage recueilli auprès de {witness.full_name}.",
                reliability,
                citizen_id=witness.id,
            )

        if incident.victim_ids:
            victim = self.citizens.get(incident.victim_ids[0])
            if victim is not None and victim.health < 99.0:
                self._add_evidence(
                    investigation,
                    "medical_report",
                    f"Constat médical des blessures de {victim.full_name}.",
                    0.88,
                    citizen_id=victim.id,
                )

        if incident.incident_type == "theft":
            if self.rng.random() < 0.72:
                self._add_evidence(
                    investigation,
                    "camera_or_property",
                    "Images de surveillance ou objet volé permettant de relier un suspect aux faits.",
                    self.rng.uniform(0.68, 0.94),
                    citizen_id=incident.offender_id,
                )
        elif incident.conflict_level >= 3 and self.rng.random() < 0.65:
            self._add_evidence(
                investigation,
                "officer_observation",
                "Les agents constatent directement des traces concordantes sur les lieux.",
                self.rng.uniform(0.72, 0.94),
                citizen_id=incident.offender_id,
            )

        if incident.offender_id is not None:
            investigation.suspect_ids.append(incident.offender_id)
            investigation.lead_suspect_id = incident.offender_id

        investigation.confidence = self._investigation_confidence(investigation)
        if investigation.lead_suspect_id is not None and investigation.confidence >= 48.0:
            investigation.status = InvestigationStatus.SUSPECT_IDENTIFIED
            investigation.notes.append("Un suspect principal est identifié à partir des premiers éléments.")
        if investigation.lead_suspect_id is not None and investigation.confidence >= 70.0:
            self._arrest_suspect(investigation, reason="preuves recueillies sur les lieux")
        else:
            self._emit(
                "investigation_opened",
                f"L'enquête #{investigation.id} est ouverte pour l'incident « {incident.title} ».",
                citizen_ids=incident.citizen_ids,
                building_id=incident.building_id,
                severity="warning",
                incident_id=incident.id,
            )
        return investigation

    def _charges_for_incident(self, incident: Incident) -> list[str]:
        mapping = {
            "theft": ["vol"],
            "fight": ["violences réciproques"],
            "assault": ["violences volontaires"],
            "serious_assault": ["violences volontaires aggravées"],
            "heated_dispute": ["trouble à l'ordre public"],
        }
        return mapping.get(incident.incident_type, ["infraction liée à l'incident"])

    def _arrest_suspect(self, investigation: Investigation, *, reason: str) -> None:
        if investigation.lead_suspect_id is None or investigation.status == InvestigationStatus.ARRESTED:
            return
        suspect = self.citizens.get(investigation.lead_suspect_id)
        incident = self.incidents.get(investigation.incident_id)
        if suspect is None or incident is None:
            return
        investigation.status = InvestigationStatus.ARRESTED
        investigation.arrest_tick = self.tick
        investigation.updated_tick = self.tick
        investigation.notes.append(f"Arrestation motivée par : {reason}.")
        suspect.arrests += 1
        if not any(
            measure.incident_id == incident.id and measure.measure_type == "custody"
            for measure in suspect.police_history[-4:]
        ):
            apply_police_measure(
                self,
                suspect,
                incident.id,
                "custody",
                240,
                reason,
                incident.police_officer_ids,
            )
        else:
            suspect.detained_until_tick = max(suspect.detained_until_tick or 0, self.tick + 240)
            suspect.current_detention_type = "custody"
        self.arrests_today += 1

        case = JudicialCase(
            id=self._next_case_id,
            investigation_id=investigation.id,
            incident_id=incident.id,
            defendant_id=suspect.id,
            charges=self._charges_for_incident(incident),
            status=JudicialCaseStatus.AWAITING_HEARING,
            filed_tick=self.tick,
            hearing_tick=self.tick + self.rng.randint(720, 2160),
            evidence_score=investigation.confidence,
        )
        self._next_case_id += 1
        self.judicial_cases[case.id] = case
        investigation.case_id = case.id
        investigation.status = InvestigationStatus.REFERRED
        suspect.active_case_ids.append(case.id)
        self.cases_filed_today += 1
        self._emit(
            "suspect_arrested",
            f"{suspect.full_name} est arrêté ; le dossier #{case.id} est transmis à la justice.",
            citizen_ids=(suspect.id, *incident.victim_ids),
            building_id=incident.building_id,
            severity="danger",
            incident_id=incident.id,
        )

    def _advance_justice(self) -> None:
        justice_hour = self.total_minutes // 60
        if getattr(self, "_last_justice_hour", -1) == justice_hour:
            return
        self._last_justice_hour = justice_hour

        for investigation in self.investigations.values():
            if investigation.status not in {InvestigationStatus.OPEN, InvestigationStatus.SUSPECT_IDENTIFIED}:
                continue
            if self.tick - investigation.updated_tick < 360:
                continue
            incident = self.incidents.get(investigation.incident_id)
            if incident is None:
                continue
            if investigation.lead_suspect_id is None and incident.offender_id is not None and self.rng.random() < 0.45:
                investigation.lead_suspect_id = incident.offender_id
                investigation.suspect_ids.append(incident.offender_id)
                investigation.status = InvestigationStatus.SUSPECT_IDENTIFIED
            reliability = self.rng.uniform(0.35, 0.72)
            self._add_evidence(
                investigation,
                "follow_up",
                "Vérification complémentaire réalisée par les enquêteurs.",
                reliability,
                citizen_id=investigation.lead_suspect_id,
            )
            investigation.confidence = self._investigation_confidence(investigation)
            if investigation.lead_suspect_id is not None and investigation.confidence >= 72.0:
                self._arrest_suspect(investigation, reason="recoupements de l'enquête")
            elif self.tick - investigation.opened_tick > 5 * 24 * 60 and investigation.confidence < 45.0:
                investigation.status = InvestigationStatus.CLOSED
                investigation.notes.append("Enquête classée faute d'éléments suffisants.")

        for case in self.judicial_cases.values():
            if case.status != JudicialCaseStatus.AWAITING_HEARING or self.tick < case.hearing_tick:
                continue
            defendant = self.citizens.get(case.defendant_id)
            incident = self.incidents.get(case.incident_id)
            if defendant is None or incident is None:
                case.status = JudicialCaseStatus.DISMISSED
                case.verdict = "classé"
                continue
            conviction_threshold = 61.0 + self.rng.uniform(-8.0, 8.0)
            case.decided_tick = self.tick
            if case.evidence_score >= conviction_threshold:
                case.status = JudicialCaseStatus.DECIDED
                case.verdict = "coupable"
                if incident.incident_type == "theft":
                    fine = round(self.rng.uniform(90.0, 360.0), 2)
                    defendant.money = round(max(0.0, defendant.money - fine), 2)
                    case.sentence = f"amende de {fine:.0f} € et probation"
                elif incident.incident_type == "serious_assault":
                    detention = self.rng.randint(2, 5) * 24 * 60
                    defendant.detained_until_tick = max(defendant.detained_until_tick or 0, self.tick + detention)
                    case.sentence = f"détention de {detention // (24 * 60)} jours"
                else:
                    detention = self.rng.randint(6, 18) * 60
                    defendant.detained_until_tick = max(defendant.detained_until_tick or 0, self.tick + detention)
                    case.sentence = f"détention de {detention // 60} heures et probation"
                message = f"Le dossier #{case.id} est jugé : {defendant.full_name} est déclaré coupable ({case.sentence})."
            else:
                case.status = JudicialCaseStatus.DISMISSED
                case.verdict = "relaxé"
                case.sentence = "aucune peine"
                defendant.detained_until_tick = None
                message = f"Le dossier #{case.id} est jugé : {defendant.full_name} est relaxé faute de preuves suffisantes."
            self._update_conflict_outcome(incident, message)
            investigation = self.investigations.get(case.investigation_id)
            if investigation is not None:
                investigation.status = InvestigationStatus.CLOSED
                investigation.updated_tick = self.tick
            self._emit(
                "case_decided",
                message,
                citizen_ids=(defendant.id, *incident.victim_ids),
                building_id=incident.building_id,
                severity="warning" if case.verdict == "coupable" else "info",
                incident_id=incident.id,
            )

    def _move_cars(self) -> None:
        occupancy = self._moving_vehicle_occupancy()
        for car in self.vehicles.values():
            if car.vehicle_type != VehicleType.CAR or car.status != VehicleStatus.DRIVING:
                continue
            if not car.passenger_ids:
                car.status = VehicleStatus.PARKED
                continue
            owner_id = min(car.passenger_ids)
            citizen = self.citizens[owner_id]

            for _ in range(self.CAR_SPEED):
                if car.route_index >= len(car.route):
                    break
                next_cell = car.route[car.route_index]
                if self._vehicle_delayed(car, next_cell, occupancy):
                    citizen.needs.stress = min(100.0, citizen.needs.stress + 0.08)
                    break
                occupancy[(car.x, car.y)] -= 1
                car.x, car.y = next_cell
                car.route_index += 1
                car.distance_today += 1
                occupancy[next_cell] += 1
                citizen.x, citizen.y = next_cell
                citizen.trip_distance += 1

            if car.route_index >= len(car.route):
                self._finish_trip(citizen)

    def _moving_vehicle_occupancy(self) -> Counter[tuple[int, int]]:
        return Counter(
            (vehicle.x, vehicle.y)
            for vehicle in self.vehicles.values()
            if vehicle.status in {
                VehicleStatus.DRIVING, VehicleStatus.IN_SERVICE,
                VehicleStatus.RESPONDING, VehicleStatus.RETURNING,
            }
        )

    def _vehicle_delayed(
        self,
        vehicle: Vehicle,
        next_cell: tuple[int, int],
        occupancy: Counter[tuple[int, int]],
    ) -> bool:
        density = occupancy[next_cell]
        delayed = density >= 4 or (density >= 2 and (self.tick + vehicle.id) % 3 == 0)
        if delayed:
            vehicle.delay_minutes += 1
            self.traffic_delay_today += 1
        return delayed

    def _finish_trip(self, citizen: Citizen) -> None:
        destination = self.buildings.get(citizen.destination_building_id)
        if destination is None:
            return
        citizen.x, citizen.y = destination.entrance
        destination.occupants.add(citizen.id)

        if citizen.active_vehicle_id is not None:
            vehicle = self.vehicles.get(citizen.active_vehicle_id)
            if vehicle is not None:
                vehicle.passenger_ids.discard(citizen.id)
                if vehicle.vehicle_type == VehicleType.CAR:
                    vehicle.status = VehicleStatus.PARKED
                    vehicle.route = []
                    vehicle.route_index = 0
                    vehicle.target_building_id = None
                    vehicle.current_building_id = destination.id
                    fuel_cost = round(citizen.trip_distance * 0.05, 2)
                    citizen.money = round(max(0.0, citizen.money - fuel_cost), 2)

        citizen.active_vehicle_id = None
        citizen.last_transport_mode = citizen.transport_mode
        citizen.travel_stage = TravelStage.IDLE
        citizen.route = []
        citizen.route_index = 0
        citizen.origin_stop_id = None
        citizen.destination_stop_id = None
        citizen.waiting_since_tick = None
        if citizen.trip_started_tick is not None:
            citizen.last_trip_minutes = max(1, self.tick - citizen.trip_started_tick)
            citizen.travel_minutes_today += citizen.last_trip_minutes
        citizen.trip_started_tick = None
        citizen.activity = citizen.planned_activity
        if destination.building_type != BuildingType.HOME:
            citizen.favorite_place_visits[destination.id] = citizen.favorite_place_visits.get(destination.id, 0) + 1
        self._emit(
            "citizen_arrived",
            f"{citizen.full_name} arrive à {destination.name} en {citizen.last_trip_minutes} min.",
            citizen_ids=(citizen.id,),
            building_id=destination.id,
        )

    def _resolve_activities(self) -> None:
        for citizen in self.citizens.values():
            if citizen.travel_stage != TravelStage.IDLE:
                continue
            destination_id = citizen.destination_building_id
            if destination_id is None:
                continue
            destination = self.buildings[destination_id]
            if (citizen.x, citizen.y) != destination.entrance:
                continue

            citizen.activity = citizen.planned_activity
            if citizen.activity == Activity.EATING:
                citizen.needs.hunger = max(0.0, citizen.needs.hunger - 0.8)
                if self.minute == 0 and citizen.money >= 8:
                    citizen.money = round(citizen.money - 8.0, 2)
            elif citizen.activity == Activity.WORKING:
                # La présence, la performance et la paie sont gérées par le système de travail.
                citizen.needs.stress = min(100.0, citizen.needs.stress + 0.004)
            elif citizen.activity == Activity.SHOPPING:
                citizen.needs.stress = max(0.0, citizen.needs.stress - 0.01)
            elif citizen.activity == Activity.SLEEPING:
                citizen.needs.fatigue = max(0.0, citizen.needs.fatigue - 0.2)

    def _resolve_social_life(self) -> None:
        resolve_ambient_social_life(self)

    def create_incident(
        self,
        *,
        incident_type: str,
        title: str,
        description: str,
        severity: str,
        citizen_ids: tuple[int, ...] = (),
        offender_id: int | None = None,
        victim_ids: tuple[int, ...] = (),
        witness_ids: tuple[int, ...] = (),
        building_id: int | None = None,
        vehicle_id: int | None = None,
        reported: bool = False,
        lifetime_minutes: int = 180,
        conflict_level: int = 0,
    ) -> Incident:
        building = self.buildings.get(building_id) if building_id is not None else None
        vehicle = self.vehicles.get(vehicle_id) if vehicle_id is not None else None
        if vehicle is not None:
            x, y = vehicle.x, vehicle.y
        elif building is not None:
            x, y = building.entrance
        elif citizen_ids:
            citizen = self.citizens[citizen_ids[0]]
            x, y = citizen.x, citizen.y
        else:
            x, y = 0, 0

        status = IncidentStatus.REPORTED if reported else IncidentStatus.ACTIVE
        incident = Incident(
            id=self._next_incident_id,
            incident_type=incident_type,
            title=title,
            description=description,
            severity=severity,
            citizen_ids=tuple(dict.fromkeys(citizen_ids)),
            offender_id=offender_id,
            victim_ids=victim_ids,
            witness_ids=witness_ids,
            building_id=building_id,
            vehicle_id=vehicle_id,
            x=x,
            y=y,
            created_tick=self.tick,
            expires_tick=self.tick + lifetime_minutes,
            status=status,
            reported=reported,
            conflict_level=conflict_level,
        )
        self._next_incident_id += 1
        self.incidents[incident.id] = incident
        self._emit(
            incident_type,
            description,
            citizen_ids=incident.citizen_ids,
            building_id=building_id,
            vehicle_id=vehicle_id,
            severity=severity,
            incident_id=incident.id,
        )
        return incident

    def create_conflict_incident(
        self,
        a: Citizen,
        b: Citizen,
        building_id: int,
        level: int,
        *,
        repeat: bool = False,
    ) -> Incident:
        building = self.buildings[building_id]
        level = max(1, min(5, level))
        offender, victim = sorted(
            (a, b),
            key=lambda citizen: (
                citizen.agreeableness
                - citizen.aggression * 0.7
                - citizen.impulsivity * 0.35
                - citizen.needs.stress * 0.35,
                citizen.id,
            ),
        )
        witnesses = tuple(
            citizen_id for citizen_id in sorted(building.occupants)
            if citizen_id not in {a.id, b.id}
        )[:8]
        labels = {
            1: ("dispute", "Dispute", "warning", 90),
            2: ("heated_dispute", "Grosse dispute", "warning", 150),
            3: ("fight", "Bagarre", "danger", 240),
            4: ("assault", "Agression", "danger", 360),
            5: ("serious_assault", "Agression grave", "danger", 600),
        }
        incident_type, title, severity, lifetime = labels[level]
        if repeat:
            title = f"{title} répétée"
        reported_probability = {1: 0.05, 2: 0.28, 3: 0.68, 4: 0.9, 5: 0.99}[level]
        reported = bool(witnesses) and self.rng.random() < reported_probability

        damage = 0.0
        if level == 3:
            damage = self.rng.uniform(2.0, 6.0)
        elif level == 4:
            damage = self.rng.uniform(8.0, 16.0)
        elif level == 5:
            damage = self.rng.uniform(18.0, 32.0)
        if damage:
            victim.health = max(0.0, victim.health - damage)
            victim.victimizations += 1
            offender.offenses_committed += 1
            victim.needs.stress = min(100.0, victim.needs.stress + damage * 0.8)
            offender.needs.stress = min(100.0, offender.needs.stress + damage * 0.25)

        descriptions = {
            1: f"Une dispute oppose {a.full_name} et {b.full_name} à {building.name}.",
            2: f"La dispute entre {a.full_name} et {b.full_name} devient particulièrement virulente à {building.name}.",
            3: f"Le conflit entre {a.full_name} et {b.full_name} dégénère en bagarre à {building.name}.",
            4: f"{offender.full_name} agresse {victim.full_name} à {building.name}.",
            5: f"{victim.full_name} subit une agression grave impliquant {offender.full_name} à {building.name}.",
        }
        description = descriptions[level]
        if reported:
            description += " Des témoins préviennent la police."

        # Une escalade remplace visuellement les incidents moins graves encore actifs du même duo.
        pair = {a.id, b.id}
        for previous in self.incidents.values():
            if previous.status in {IncidentStatus.EXPIRED, IncidentStatus.RESOLVED}:
                continue
            if pair.issubset(set(previous.citizen_ids)) and previous.conflict_level < level:
                previous.status = IncidentStatus.RESOLVED
                previous.resolved_tick = self.tick
                previous.resolution = "Incident dépassé par une escalade plus grave."
                previous.expires_tick = min(previous.expires_tick, self.tick + 20)

        incident = self.create_incident(
            incident_type=incident_type,
            title=title,
            description=description,
            severity=severity,
            citizen_ids=(a.id, b.id, *witnesses),
            offender_id=offender.id if level >= 3 else None,
            victim_ids=(victim.id,) if level >= 3 else (),
            witness_ids=witnesses,
            building_id=building_id,
            reported=reported,
            lifetime_minutes=lifetime,
            conflict_level=level,
        )
        self._remember_conflict(a, b, incident, offender_id=offender.id if level >= 3 else None)
        return incident

    def _remember_conflict(
        self,
        a: Citizen,
        b: Citizen,
        incident: Incident,
        *,
        offender_id: int | None,
    ) -> None:
        building_id = incident.building_id
        for citizen, other in ((a, b), (b, a)):
            relationship = citizen.relationships.setdefault(other.id, Relationship(other_id=other.id))
            role = "auteur" if offender_id == citizen.id else "victime" if offender_id == other.id else "participant"
            relationship.conflict_history.append(
                ConflictRecord(
                    tick=self.tick,
                    level=incident.conflict_level,
                    label=conflict_label(relationship),
                    title=incident.title,
                    incident_id=incident.id,
                    building_id=building_id,
                    role=role,
                )
            )
            relationship.conflict_history[:] = relationship.conflict_history[-30:]
            relationship.last_conflict_tick = self.tick
            relationship.peak_conflict_level = max(
                relationship.peak_conflict_level,
                incident.conflict_level,
            )

    def _update_conflict_outcome(self, incident: Incident, outcome: str) -> None:
        for citizen_id in incident.citizen_ids[:2]:
            citizen = self.citizens.get(citizen_id)
            if citizen is None:
                continue
            for relationship in citizen.relationships.values():
                for record in relationship.conflict_history:
                    if record.incident_id == incident.id:
                        record.outcome = outcome

    def _resolve_incidents(self) -> None:
        incident_hour = self.total_minutes // 60
        if incident_hour == self._last_incident_hour:
            return
        self._last_incident_hour = incident_hour

        shops = [
            building
            for building in self.buildings.values()
            if building.building_type in {BuildingType.SHOP, BuildingType.CAFE}
        ]
        if not shops or self.rng.random() >= 0.12:
            return

        building = self.rng.choice(shops)
        possible_offenders = [
            self.citizens[citizen_id]
            for citizen_id in building.occupants
            if self.citizens[citizen_id].money < 250.0
        ]
        if not possible_offenders:
            return

        offender = self.rng.choice(possible_offenders)
        stolen_value = round(self.rng.uniform(8.0, 45.0), 2)
        offender.money = round(offender.money + stolen_value, 2)
        offender.offenses_committed += 1
        witnesses = tuple(
            citizen_id for citizen_id in sorted(building.occupants)
            if citizen_id != offender.id
        )[:8]
        reported = bool(witnesses) and self.rng.random() < 0.7
        suffix = "Le vol est signalé." if reported else "Personne ne semble l'avoir remarqué."
        self.create_incident(
            incident_type="theft",
            title="Petit vol",
            description=(
                f"Un vol de {stolen_value:.0f} € implique {offender.full_name} "
                f"à {building.name}. {suffix}"
            ),
            severity="danger" if reported else "warning",
            citizen_ids=(offender.id, *witnesses),
            offender_id=offender.id,
            witness_ids=witnesses,
            building_id=building.id,
            reported=reported,
            lifetime_minutes=300 if reported else 160,
        )

    def _dispatch_police(self) -> None:
        refresh_police_crews(self)
        available_units = [
            vehicle for vehicle in self.vehicles.values()
            if vehicle.vehicle_type == VehicleType.POLICE
            and vehicle.status == VehicleStatus.PARKED
            and len(vehicle.crew_ids) >= min(2, vehicle.capacity)
        ]
        if not available_units:
            return
        pending = sorted(
            (
                incident for incident in self.incidents.values()
                if incident.reported and incident.status == IncidentStatus.REPORTED
            ),
            key=lambda incident: (incident.severity != "danger", incident.created_tick, incident.id),
        )
        for incident, unit in zip(pending, available_units):
            unit.status = VehicleStatus.RESPONDING
            unit.incident_id = incident.id
            unit.service_started_tick = self.tick
            unit.current_building_id = None
            unit.target_building_id = incident.building_id
            unit.route = road_path((unit.x, unit.y), (incident.x, incident.y), self.road_cells)
            unit.route_index = 0
            unit.passenger_ids = set(unit.crew_ids)
            self._sync_police_crew(unit)
            incident.status = IncidentStatus.RESPONDING
            incident.police_vehicle_id = unit.id
            incident.police_officer_ids = tuple(sorted(unit.crew_ids))
            incident.dispatched_tick = self.tick
            officer_names = ", ".join(self.citizens[citizen_id].full_name for citizen_id in sorted(unit.crew_ids))
            self._emit(
                "police_dispatched",
                f"L'unité #{unit.id}, composée de {officer_names}, est envoyée sur l'incident « {incident.title} ».",
                citizen_ids=tuple(dict.fromkeys((*incident.citizen_ids, *unit.crew_ids))),
                building_id=incident.building_id,
                vehicle_id=unit.id,
                severity="warning",
                incident_id=incident.id,
            )

    def _expire_incidents(self) -> None:
        for incident in self.incidents.values():
            if incident.status == IncidentStatus.EXPIRED:
                continue
            if self.tick < incident.expires_tick:
                continue
            if incident.status in {IncidentStatus.RESPONDING, IncidentStatus.ON_SCENE}:
                incident.expires_tick = self.tick + 30
                continue
            incident.status = IncidentStatus.EXPIRED

    def _report_traffic_if_needed(self) -> None:
        traffic_hour = self.total_minutes // 60
        if traffic_hour == self._last_traffic_event_hour:
            return
        self._last_traffic_event_hour = traffic_hour
        congestion = self._congestion_cells()
        heavy = [row for row in congestion if row["level"] == "heavy"]
        if heavy:
            self._emit(
                "traffic_congestion",
                f"La circulation est fortement ralentie sur {len(heavy)} portion(s) du réseau.",
                severity="warning",
            )

    def _first_building(self, building_type: BuildingType) -> Building | None:
        return next((building for building in self.buildings.values() if building.building_type == building_type), None)

    def _remove_from_all_buildings(self, citizen_id: int) -> None:
        for building in self.buildings.values():
            building.occupants.discard(citizen_id)

    def _emit(
        self,
        event_type: str,
        message: str,
        *,
        citizen_ids: tuple[int, ...] = (),
        building_id: int | None = None,
        vehicle_id: int | None = None,
        severity: str = "info",
        incident_id: int | None = None,
    ) -> None:
        event = DomainEvent(
            id=self._next_event_id,
            tick=self.tick,
            day=self.day,
            hour=self.hour,
            minute=self.minute,
            event_type=event_type,
            message=message,
            citizen_ids=citizen_ids,
            building_id=building_id,
            vehicle_id=vehicle_id,
            severity=severity,
            incident_id=incident_id,
        )
        self._next_event_id += 1
        self.events.append(event)
        if len(self.events) > 500:
            self.events = self.events[-500:]

    def get_citizen_detail(self, citizen_id: int) -> dict[str, Any]:
        citizen = self.citizens[citizen_id]
        relationship_rows = []
        for relationship in sorted(
            citizen.relationships.values(),
            key=lambda relation: (
                relation.conflict_level,
                relation.peak_conflict_level,
                abs(relation.affection),
                relation.familiarity,
            ),
            reverse=True,
        )[:30]:
            other = self.citizens[relationship.other_id]
            relationship_rows.append(
                {
                    "citizenId": other.id,
                    "name": other.full_name,
                    "familiarity": round(relationship.familiarity, 1),
                    "affection": round(relationship.affection, 1),
                    "trust": round(relationship.trust, 1),
                    "status": relationship_label(relationship),
                    "positiveInteractions": relationship.positive_interactions,
                    "negativeInteractions": relationship.negative_interactions,
                    "lastInteractionTick": relationship.last_interaction_tick,
                    "consecutiveNegativeInteractions": relationship.consecutive_negative_interactions,
                    "conflictScore": round(relationship.conflict_score, 1),
                    "conflictLevel": relationship.conflict_level,
                    "conflictLabel": conflict_label(relationship),
                    "peakConflictLevel": relationship.peak_conflict_level,
                    "lastConflictTick": relationship.last_conflict_tick,
                    "conflictHistory": [
                        {
                            "tick": record.tick,
                            "level": record.level,
                            "label": record.label,
                            "title": record.title,
                            "incidentId": record.incident_id,
                            "buildingId": record.building_id,
                            "buildingName": (
                                self.buildings[record.building_id].name
                                if record.building_id in self.buildings else None
                            ),
                            "role": record.role,
                            "outcome": record.outcome,
                        }
                        for record in reversed(relationship.conflict_history[-12:])
                    ],
                }
            )

        home = self.buildings[citizen.home_id]
        workplace = self.buildings.get(citizen.workplace_id) if citizen.workplace_id else None
        destination = self.buildings.get(citizen.destination_building_id) if citizen.destination_building_id else None
        owned_vehicle = self.vehicles.get(citizen.owned_vehicle_id) if citizen.owned_vehicle_id else None
        active_vehicle = self.vehicles.get(citizen.active_vehicle_id) if citizen.active_vehicle_id else None
        origin_stop = self.bus_stops.get(citizen.origin_stop_id) if citizen.origin_stop_id else None
        destination_stop = self.bus_stops.get(citizen.destination_stop_id) if citizen.destination_stop_id else None
        household = self.households.get(citizen.household_id) if citizen.household_id else None
        household_members = [
            self.citizens[member_id]
            for member_id in (household.member_ids if household else [])
            if member_id != citizen.id
        ]
        favorite_places = [
            {"id": building_id, "name": self.buildings[building_id].name, "visits": visits}
            for building_id, visits in sorted(
                citizen.favorite_place_visits.items(), key=lambda item: (item[1], -item[0]), reverse=True
            )[:5]
            if building_id in self.buildings
        ]
        social_event = self.social_events.get(citizen.social_event_id) if citizen.social_event_id else None
        conflict_history = sorted(
            (
                {
                    "otherId": relationship.other_id,
                    "otherName": self.citizens[relationship.other_id].full_name,
                    "tick": record.tick,
                    "level": record.level,
                    "label": record.label,
                    "title": record.title,
                    "incidentId": record.incident_id,
                    "buildingId": record.building_id,
                    "buildingName": (
                        self.buildings[record.building_id].name
                        if record.building_id in self.buildings else None
                    ),
                    "role": record.role,
                    "outcome": record.outcome,
                }
                for relationship in citizen.relationships.values()
                for record in relationship.conflict_history
            ),
            key=lambda row: row["tick"],
            reverse=True,
        )[:60]
        citizen_cases = sorted(
            (case for case in self.judicial_cases.values() if case.defendant_id == citizen.id),
            key=lambda case: case.filed_tick,
            reverse=True,
        )
        citizen_investigations = sorted(
            (
                investigation for investigation in self.investigations.values()
                if investigation.lead_suspect_id == citizen.id
                or citizen.id in investigation.suspect_ids
                or (
                    investigation.incident_id in self.incidents
                    and citizen.id in self.incidents[investigation.incident_id].citizen_ids
                )
            ),
            key=lambda investigation: investigation.opened_tick,
            reverse=True,
        )

        return {
            "kind": "citizen",
            "currentTick": self.tick,
            **self._citizen_summary(citizen),
            "age": citizen.age,
            "home": {"id": home.id, "name": home.name},
            "workplace": {"id": workplace.id, "name": workplace.name} if workplace else None,
            "destination": {"id": destination.id, "name": destination.name} if destination else None,
            "jobTitle": citizen.job_title,
            "salaryDaily": citizen.salary_daily,
            "money": citizen.money,
            "health": round(citizen.health, 1),
            "employment": {
                "status": "employed" if citizen.workplace_id is not None else "unemployed",
                "workStartHour": citizen.work_start_hour,
                "workEndHour": citizen.work_end_hour,
                "workDays": list(citizen.work_days),
                "scheduledToday": weekday(self) in citizen.work_days,
                "onDuty": is_on_duty(self, citizen),
                "minutesWorkedToday": citizen.minutes_worked_today,
                "shiftsCompleted": citizen.shifts_completed,
                "missedShifts": citizen.missed_shifts,
                "performance": round(citizen.job_performance, 1),
                "satisfaction": round(citizen.job_satisfaction, 1),
                "jobSearchActive": citizen.job_search_active,
                "jobSearchSinceTick": citizen.job_search_since_tick,
                "lastJobChangeTick": citizen.last_job_change_tick,
                "incomeToday": round(citizen.income_today, 2),
                "expensesToday": round(citizen.expenses_today, 2),
                "financialStress": round(citizen.financial_stress, 1),
                "experienceByJob": {key: round(value, 1) for key, value in citizen.experience_by_job.items()},
                "applications": [
                    self._job_application_to_dict(self.job_applications[application_id])
                    for application_id in reversed(citizen.application_ids)
                    if application_id in self.job_applications
                ][:20],
                "history": [
                    self._employment_record_to_dict(record)
                    for record in reversed(citizen.employment_history)
                ][:20],
            },
            "consumption": {
                "foodUnits": round(citizen.food_units, 1),
                "goodsUnits": round(citizen.goods_units, 1),
                "shoppingVisits": citizen.shopping_visits,
                "lastShoppingTick": citizen.last_shopping_tick,
                "intoxication": round(citizen.intoxication, 1),
            },
            "criminality": {
                "offensesCommitted": citizen.offenses_committed,
                "victimizations": citizen.victimizations,
                "arrests": citizen.arrests,
            },
            "needs": {
                "hunger": round(citizen.needs.hunger, 1),
                "fatigue": round(citizen.needs.fatigue, 1),
                "stress": round(citizen.needs.stress, 1),
                "social": round(citizen.needs.social, 1),
            },
            "decisionReason": citizen.last_decision_reason,
            "relationships": relationship_rows,
            "personality": {
                "sociability": round(citizen.sociability, 1),
                "agreeableness": round(citizen.agreeableness, 1),
                "spontaneity": round(citizen.spontaneity, 1),
                "aggression": round(citizen.aggression, 1),
                "impulsivity": round(citizen.impulsivity, 1),
                "grudgeTendency": round(citizen.grudge_tendency, 1),
                "conflictPropensity": round(conflict_propensity(citizen) * 100.0, 1),
                "temperament": temperament_label(citizen),
            },
            "household": (
                {
                    "id": household.id,
                    "homeId": household.home_id,
                    "cohesion": round(household.cohesion, 1),
                    "sharedMeals": household.shared_meals,
                    "conflicts": household.conflicts,
                    "incomeToday": round(household.income_today, 2),
                    "recurringExpensesToday": round(household.recurring_expenses_today, 2),
                    "foodExpensesToday": round(household.food_expenses_today, 2),
                    "goodsExpensesToday": round(household.goods_expenses_today, 2),
                    "debt": round(household.debt, 2),
                    "overdraftLimit": round(household.overdraft_limit, 2),
                    "financialStress": round(household.financial_stress, 1),
                    "budgets": {
                        "foodDaily": round(household.food_budget_daily, 2),
                        "goodsDaily": round(household.goods_budget_daily, 2),
                    },
                    "financialHistory": [
                        self._household_financial_to_dict(record)
                        for record in reversed(household.financial_history)
                    ][:14],
                    "members": [
                        {"id": member.id, "name": member.full_name} for member in household_members
                    ],
                }
                if household else None
            ),
            "social": {
                "interactionsToday": citizen.social_interactions_today,
                "invitationsSent": citizen.invitations_sent,
                "invitationsAccepted": citizen.invitations_accepted,
                "favoritePlaces": favorite_places,
                "event": self._social_event_to_dict(social_event) if social_event else None,
            },
            "conflictHistory": conflict_history,
            "justice": {
                "detained": citizen.detained_until_tick is not None and self.tick < citizen.detained_until_tick,
                "detainedUntilTick": citizen.detained_until_tick,
                "detentionType": citizen.current_detention_type,
                "policeHistory": [
                    {
                        "tick": item.tick,
                        "incidentId": item.incident_id,
                        "measureType": item.measure_type,
                        "label": item.label,
                        "durationMinutes": item.duration_minutes,
                        "reason": item.reason,
                        "officers": [self._citizen_ref(officer_id) for officer_id in item.officer_ids],
                    }
                    for item in reversed(citizen.police_history[-20:])
                ],
                "investigations": [
                    {
                        "id": investigation.id,
                        "incidentId": investigation.incident_id,
                        "status": investigation.status.value,
                        "confidence": round(investigation.confidence, 1),
                        "openedTick": investigation.opened_tick,
                        "caseId": investigation.case_id,
                    }
                    for investigation in citizen_investigations[:12]
                ],
                "cases": [self._case_summary(case) for case in citizen_cases[:12]],
            },
            "transport": {
                "mode": citizen.transport_mode.value,
                "lastMode": citizen.last_transport_mode.value,
                "stage": citizen.travel_stage.value,
                "ownedVehicle": (
                    {"id": owned_vehicle.id, "type": owned_vehicle.vehicle_type.value}
                    if owned_vehicle else None
                ),
                "activeVehicle": (
                    {"id": active_vehicle.id, "type": active_vehicle.vehicle_type.value}
                    if active_vehicle else None
                ),
                "originStop": {"id": origin_stop.id, "name": origin_stop.name} if origin_stop else None,
                "destinationStop": (
                    {"id": destination_stop.id, "name": destination_stop.name}
                    if destination_stop else None
                ),
                "lastTripMinutes": citizen.last_trip_minutes,
                "travelMinutesToday": citizen.travel_minutes_today,
                "tripsToday": citizen.trips_today,
            },
        }

    def get_vehicle_detail(self, vehicle_id: int) -> dict[str, Any]:
        vehicle = self.vehicles[vehicle_id]
        owner = self.citizens.get(vehicle.owner_id) if vehicle.owner_id else None
        line = self.bus_lines.get(vehicle.line_id) if vehicle.line_id else None
        target = self.buildings.get(vehicle.target_building_id) if vehicle.target_building_id else None
        passengers = [self.citizens[citizen_id] for citizen_id in sorted(vehicle.passenger_ids)]
        route_length = len(vehicle.route)
        progress = 0.0 if route_length == 0 else (vehicle.route_index % route_length) / route_length * 100
        return {
            "kind": "vehicle",
            **self._vehicle_summary(vehicle),
            "owner": {"id": owner.id, "name": owner.full_name} if owner else None,
            "line": {"id": line.id, "name": line.name} if line else None,
            "target": {"id": target.id, "name": target.name} if target else None,
            "passengers": [{"id": passenger.id, "name": passenger.full_name} for passenger in passengers],
            "crew": [
                {"id": officer.id, "name": officer.full_name, "onDuty": is_on_duty(self, officer)}
                for officer_id in sorted(vehicle.crew_ids)
                if (officer := self.citizens.get(officer_id)) is not None
            ],
            "delayMinutes": vehicle.delay_minutes,
            "distanceToday": vehicle.distance_today,
            "routeProgress": round(progress, 1),
            "incident": (
                {"id": vehicle.incident_id, "title": self.incidents[vehicle.incident_id].title}
                if vehicle.incident_id in self.incidents else None
            ),
        }

    def get_incident_detail(self, incident_id: int) -> dict[str, Any]:
        incident = self.incidents[incident_id]
        building = self.buildings.get(incident.building_id) if incident.building_id else None
        police_vehicle = self.vehicles.get(incident.police_vehicle_id) if incident.police_vehicle_id else None
        return {
            "kind": "incident",
            **self._incident_summary(incident),
            "description": incident.description,
            "building": {"id": building.id, "name": building.name} if building else None,
            "offender": self._citizen_ref(incident.offender_id),
            "victims": [self._citizen_ref(citizen_id) for citizen_id in incident.victim_ids],
            "witnesses": [self._citizen_ref(citizen_id) for citizen_id in incident.witness_ids],
            "involved": [self._citizen_ref(citizen_id) for citizen_id in incident.citizen_ids],
            "policeVehicle": (
                {"id": police_vehicle.id, "type": police_vehicle.vehicle_type.value}
                if police_vehicle else None
            ),
            "timeline": {
                "createdTick": incident.created_tick,
                "dispatchedTick": incident.dispatched_tick,
                "arrivalTick": incident.police_arrival_tick,
                "resolvedTick": incident.resolved_tick,
            },
            "resolution": incident.resolution,
            "policeAction": incident.police_action,
            "policeOfficers": [self._citizen_ref(citizen_id) for citizen_id in incident.police_officer_ids],
            "detained": [self._citizen_ref(citizen_id) for citizen_id in incident.detained_ids],
            "investigation": self._investigation_detail(incident.investigation_id),
        }

    def get_building_detail(self, building_id: int) -> dict[str, Any]:
        building = self.buildings[building_id]
        employees = sorted(
            (citizen for citizen in self.citizens.values() if citizen.workplace_id == building.id),
            key=lambda citizen: (not is_on_duty(self, citizen), citizen.full_name),
        )
        occupants = [self.citizens[citizen_id] for citizen_id in sorted(building.occupants) if citizen_id in self.citizens]
        return {
            "kind": "building",
            **self._building_to_dict(building),
            "employees": [
                {
                    "id": employee.id,
                    "name": employee.full_name,
                    "jobTitle": employee.job_title,
                    "onDuty": is_on_duty(self, employee),
                    "shift": f"{employee.work_start_hour:02d}:00–{employee.work_end_hour:02d}:00",
                    "performance": round(employee.job_performance, 1),
                    "satisfaction": round(employee.job_satisfaction, 1),
                }
                for employee in employees
            ],
            "occupants": [{"id": person.id, "name": person.full_name} for person in occupants[:40]],
            "services": {
                "operational": building_operational(self, building.id),
                "staffOnDuty": staff_count(self, building.id),
                "employeesRequired": building.employees_required,
                "foodStock": round(building.food_stock, 1),
                "goodsStock": round(building.goods_stock, 1),
                "revenueToday": round(building.revenue_today, 2),
            },
            "finance": {
                "status": building.business_status.value,
                "cash": round(building.cash, 2),
                "totalRevenue": round(building.total_revenue, 2),
                "payrollToday": round(building.payroll_today, 2),
                "fixedCostsToday": round(building.fixed_costs_today, 2),
                "resultToday": round(building.result_today, 2),
                "serviceLevel": round(building.service_level, 1),
                "employeeCapacity": building.employee_capacity,
                "targetEmployees": building.target_employees,
                "openPositions": building.open_positions,
                "financialHistory": [
                    self._business_financial_to_dict(record) for record in reversed(building.financial_history)
                ][:14],
                "employmentHistory": [
                    self._employment_record_to_dict(record) for record in reversed(building.employment_events)
                ][:20],
            },
        }

    def get_enterprise_detail(self, building_id: int) -> dict[str, Any]:
        building = self.buildings[building_id]
        if not is_employer(building):
            raise KeyError(building_id)
        return self.get_building_detail(building_id)

    def get_economy_overview(self) -> dict[str, object]:
        return economy_overview(self)

    def _case_summary(self, case: JudicialCase) -> dict[str, Any]:
        defendant = self.citizens.get(case.defendant_id)
        return {
            "id": case.id,
            "investigationId": case.investigation_id,
            "incidentId": case.incident_id,
            "defendant": self._citizen_ref(case.defendant_id),
            "charges": list(case.charges),
            "status": case.status.value,
            "filedTick": case.filed_tick,
            "hearingTick": case.hearing_tick,
            "evidenceScore": round(case.evidence_score, 1),
            "decidedTick": case.decided_tick,
            "verdict": case.verdict,
            "sentence": case.sentence,
            "defendantName": defendant.full_name if defendant else None,
        }

    def _investigation_detail(self, investigation_id: int | None) -> dict[str, Any] | None:
        if investigation_id is None or investigation_id not in self.investigations:
            return None
        investigation = self.investigations[investigation_id]
        return {
            "id": investigation.id,
            "incidentId": investigation.incident_id,
            "status": investigation.status.value,
            "openedTick": investigation.opened_tick,
            "updatedTick": investigation.updated_tick,
            "suspects": [self._citizen_ref(citizen_id) for citizen_id in investigation.suspect_ids],
            "leadSuspect": self._citizen_ref(investigation.lead_suspect_id),
            "confidence": round(investigation.confidence, 1),
            "arrestTick": investigation.arrest_tick,
            "notes": list(investigation.notes),
            "evidence": [
                {
                    "id": item.id,
                    "type": item.evidence_type,
                    "description": item.description,
                    "reliability": round(item.reliability * 100.0, 1),
                    "citizen": self._citizen_ref(item.citizen_id),
                    "createdTick": item.created_tick,
                }
                for evidence_id in investigation.evidence_ids
                if (item := self.evidence.get(evidence_id)) is not None
            ],
            "case": (
                self._case_summary(self.judicial_cases[investigation.case_id])
                if investigation.case_id in self.judicial_cases else None
            ),
        }

    def get_investigation_detail(self, investigation_id: int) -> dict[str, Any]:
        detail = self._investigation_detail(investigation_id)
        if detail is None:
            raise KeyError(investigation_id)
        return {"kind": "investigation", **detail}

    def get_case_detail(self, case_id: int) -> dict[str, Any]:
        return {"kind": "case", **self._case_summary(self.judicial_cases[case_id])}

    def get_social_graph(self) -> dict[str, Any]:
        edges: list[dict[str, Any]] = []
        seen: set[tuple[int, int]] = set()
        for citizen in self.citizens.values():
            for relationship in citizen.relationships.values():
                pair = tuple(sorted((citizen.id, relationship.other_id)))
                if pair in seen or relationship.familiarity < 8:
                    continue
                seen.add(pair)
                edges.append({
                    "source": pair[0],
                    "target": pair[1],
                    "status": relationship_label(relationship),
                    "affection": round(relationship.affection, 1),
                    "trust": round(relationship.trust, 1),
                    "familiarity": round(relationship.familiarity, 1),
                    "conflictLevel": relationship.conflict_level,
                    "conflictLabel": conflict_label(relationship),
                })
        return {
            "tick": self.tick,
            "nodes": [
                {
                    "id": citizen.id,
                    "name": citizen.full_name,
                    "householdId": citizen.household_id,
                    "workplaceId": citizen.workplace_id,
                    "friendCount": sum(
                        1 for relationship in citizen.relationships.values()
                        if relationship_label(relationship) in {"friend", "close_friend"}
                    ),
                    "rivalCount": sum(
                        1 for relationship in citizen.relationships.values()
                        if relationship_label(relationship) == "rival"
                    ),
                    "conflictPropensity": round(conflict_propensity(citizen) * 100.0, 1),
                    "temperament": temperament_label(citizen),
                }
                for citizen in self.citizens.values()
            ],
            "edges": edges,
        }

    def _citizen_ref(self, citizen_id: int | None) -> dict[str, Any] | None:
        if citizen_id is None or citizen_id not in self.citizens:
            return None
        citizen = self.citizens[citizen_id]
        return {"id": citizen.id, "name": citizen.full_name}

    def snapshot(self) -> dict[str, Any]:
        payload = build_dynamic_snapshot(self)
        payload["type"] = "city_snapshot"
        payload["map"] = {"width": self.MAP_WIDTH, "height": self.MAP_HEIGHT}
        payload["roads"] = {
            "cells": [
                {"x": x, "y": y}
                for x, y in sorted(self.road_cells, key=lambda cell: (cell[1], cell[0]))
            ],
            **payload["roads"],
        }
        payload["transport"] = {
            "busStops": [self._bus_stop_to_dict(stop) for stop in self.bus_stops.values()],
            "busLines": [self._bus_line_to_dict(line) for line in self.bus_lines.values()],
            **payload["transport"],
        }
        return payload

    def delta_snapshot(self) -> dict[str, Any]:
        payload = build_dynamic_snapshot(self)
        payload["type"] = "city_delta"
        return payload

    def _congestion_cells(self) -> list[dict[str, Any]]:
        occupancy = self._moving_vehicle_occupancy()
        rows = []
        for (x, y), vehicles in sorted(occupancy.items(), key=lambda item: (item[0][1], item[0][0])):
            if vehicles < 2:
                continue
            rows.append(
                {
                    "x": x,
                    "y": y,
                    "vehicles": vehicles,
                    "level": "heavy" if vehicles >= 4 else "moderate",
                }
            )
        return rows

    def export_state(self) -> dict[str, Any]:
        return {
            "version": 7,
            "seed": self.seed,
            "tick": self.tick,
            "day": self.day,
            "hour": self.hour,
            "minute": self.minute,
            "nextEventId": self._next_event_id,
            "nextIncidentId": self._next_incident_id,
            "nextEvidenceId": self._next_evidence_id,
            "nextInvestigationId": self._next_investigation_id,
            "nextCaseId": self._next_case_id,
            "nextSocialEventId": self._next_social_event_id,
            "nextJobApplicationId": self._next_job_application_id,
            "lastSocialSlot": self._last_social_slot,
            "lastSocialPlanningDay": self._last_social_planning_day,
            "lastHouseholdSlot": self._last_household_slot,
            "lastIncidentHour": self._last_incident_hour,
            "lastTrafficEventHour": self._last_traffic_event_hour,
            "lastJusticeHour": getattr(self, "_last_justice_hour", -1),
            "lastLaborMarketDay": self._last_labor_market_day,
            "tripCountsToday": dict(self.trip_counts_today),
            "busBoardingsToday": self.bus_boardings_today,
            "trafficDelayToday": self.traffic_delay_today,
            "socialInvitationsToday": self.social_invitations_today,
            "socialAcceptancesToday": self.social_acceptances_today,
            "socialGatheringsCompleted": self.social_gatherings_completed,
            "policeResponsesToday": self.police_responses_today,
            "policeResponseMinutesToday": self.police_response_minutes_today,
            "arrestsToday": self.arrests_today,
            "casesFiledToday": self.cases_filed_today,
            "shopSalesToday": self.shop_sales_today,
            "shoppingTripsToday": self.shopping_trips_today,
            "policeWarningsToday": self.police_warnings_today,
            "policeDetentionsToday": self.police_detentions_today,
            "hiresToday": self.hires_today,
            "layoffsToday": self.layoffs_today,
            "resignationsToday": self.resignations_today,
            "publicSpendingTotal": self.public_spending_total,
            "rngState": self.rng.getstate(),
            "buildings": [self._export_building(building) for building in self.buildings.values()],
            "citizens": [self._export_citizen(citizen) for citizen in self.citizens.values()],
            "households": [self._export_household(household) for household in self.households.values()],
            "socialEvents": [self._export_social_event(event) for event in self.social_events.values()],
            "vehicles": [self._export_vehicle(vehicle) for vehicle in self.vehicles.values()],
            "incidents": [self._export_incident(incident) for incident in self.incidents.values()],
            "evidence": [self._export_evidence(item) for item in self.evidence.values()],
            "investigations": [self._export_investigation(item) for item in self.investigations.values()],
            "judicialCases": [self._export_case(item) for item in self.judicial_cases.values()],
            "jobApplications": [self._export_job_application(item) for item in self.job_applications.values()],
            "events": [self._export_event(event) for event in self.events],
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "World":
        version = int(state.get("version", 0))
        if version != 7:
            raise ValueError("Version de sauvegarde non prise en charge.")

        world = cls.__new__(cls)
        world.seed = int(state["seed"])
        world.rng = random.Random()
        world.rng.setstate(cls._nested_tuple(state["rngState"]))
        world.tick = int(state["tick"])
        world.day = int(state["day"])
        world.hour = int(state["hour"])
        world.minute = int(state["minute"])
        world._next_event_id = int(state["nextEventId"])
        world._next_incident_id = int(state.get("nextIncidentId", 1))
        world._next_evidence_id = int(state.get("nextEvidenceId", 1))
        world._next_investigation_id = int(state.get("nextInvestigationId", 1))
        world._next_case_id = int(state.get("nextCaseId", 1))
        world._next_social_event_id = int(state.get("nextSocialEventId", 1))
        world._next_job_application_id = int(state.get("nextJobApplicationId", 1))
        world._last_social_slot = int(state.get("lastSocialSlot", -1))
        world._last_social_planning_day = int(state.get("lastSocialPlanningDay", 0))
        world._last_household_slot = int(state.get("lastHouseholdSlot", -1))
        world._last_incident_hour = int(state.get("lastIncidentHour", -1))
        world._last_traffic_event_hour = int(state.get("lastTrafficEventHour", -1))
        world._last_justice_hour = int(state.get("lastJusticeHour", -1))
        world._last_labor_market_day = int(state.get("lastLaborMarketDay", 0))
        world.trip_counts_today = Counter(
            {mode.value: int(state.get("tripCountsToday", {}).get(mode.value, 0)) for mode in TransportMode}
        )
        world.bus_boardings_today = int(state.get("busBoardingsToday", 0))
        world.traffic_delay_today = int(state.get("trafficDelayToday", 0))
        world.social_invitations_today = int(state.get("socialInvitationsToday", 0))
        world.social_acceptances_today = int(state.get("socialAcceptancesToday", 0))
        world.social_gatherings_completed = int(state.get("socialGatheringsCompleted", 0))
        world.police_responses_today = int(state.get("policeResponsesToday", 0))
        world.police_response_minutes_today = int(state.get("policeResponseMinutesToday", 0))
        world.arrests_today = int(state.get("arrestsToday", 0))
        world.cases_filed_today = int(state.get("casesFiledToday", 0))
        world.shop_sales_today = float(state.get("shopSalesToday", 0.0))
        world.shopping_trips_today = int(state.get("shoppingTripsToday", 0))
        world.police_warnings_today = int(state.get("policeWarningsToday", 0))
        world.police_detentions_today = int(state.get("policeDetentionsToday", 0))
        world.hires_today = int(state.get("hiresToday", 0))
        world.layoffs_today = int(state.get("layoffsToday", 0))
        world.resignations_today = int(state.get("resignationsToday", 0))
        world.public_spending_total = float(state.get("publicSpendingTotal", 0.0))

        world.road_cells = generate_road_cells()
        world.bus_stops, world.bus_lines = generate_bus_network(world.road_cells)
        world._stops_by_position = {stop.position: stop for stop in world.bus_stops.values()}

        world.buildings = {}
        for row in state["buildings"]:
            building = Building(
                id=int(row["id"]),
                name=str(row["name"]),
                building_type=BuildingType(row["buildingType"]),
                x=int(row["x"]),
                y=int(row["y"]),
                width=int(row["width"]),
                height=int(row["height"]),
                capacity=int(row["capacity"]),
                occupants={int(value) for value in row["occupants"]},
                employees_required=int(row.get("employeesRequired", 1)),
                food_stock=float(row.get("foodStock", 0.0)),
                goods_stock=float(row.get("goodsStock", 0.0)),
                revenue_today=float(row.get("revenueToday", 0.0)),
                cash=float(row.get("cash", 0.0)),
                total_revenue=float(row.get("totalRevenue", 0.0)),
                payroll_today=float(row.get("payrollToday", 0.0)),
                fixed_costs_today=float(row.get("fixedCostsToday", 0.0)),
                result_today=float(row.get("resultToday", 0.0)),
                fixed_cost_daily=float(row.get("fixedCostDaily", 0.0)),
                employee_capacity=int(row.get("employeeCapacity", row["capacity"])),
                target_employees=int(row.get("targetEmployees", row["capacity"])),
                open_positions=int(row.get("openPositions", 0)),
                service_level=float(row.get("serviceLevel", 100.0)),
                business_status=BusinessStatus(row.get("businessStatus", "healthy")),
                deficit_days=int(row.get("deficitDays", 0)),
                productive_minutes_today=int(row.get("productiveMinutesToday", 0)),
                financial_history=[
                    BusinessFinancialRecord(
                        day=int(item["day"]),
                        revenue=float(item["revenue"]),
                        payroll=float(item["payroll"]),
                        fixed_costs=float(item["fixedCosts"]),
                        result=float(item["result"]),
                        cash=float(item["cash"]),
                        service_level=float(item["serviceLevel"]),
                        status=BusinessStatus(item["status"]),
                    )
                    for item in row.get("financialHistory", [])
                ],
                employment_events=[
                    EmploymentRecord(
                        tick=int(item["tick"]),
                        event_type=str(item["eventType"]),
                        label=str(item["label"]),
                        building_id=int(item["buildingId"]) if item.get("buildingId") is not None else None,
                        job_title=item.get("jobTitle"),
                        salary_daily=float(item.get("salaryDaily", 0.0)),
                        reason=str(item.get("reason", "")),
                    )
                    for item in row.get("employmentEvents", [])
                ],
            )
            world.buildings[building.id] = building

        if not any(building.building_type == BuildingType.POLICE for building in world.buildings.values()):
            police_id = max(world.buildings, default=0) + 1
            world.buildings[police_id] = Building(
                id=police_id,
                name="Commissariat central",
                building_type=BuildingType.POLICE,
                x=34,
                y=15,
                width=3,
                height=2,
                capacity=12,
            )

        world.citizens = {}
        for row in state["citizens"]:
            needs_row = row["needs"]
            citizen = Citizen(
                id=int(row["id"]),
                first_name=str(row["firstName"]),
                last_name=str(row["lastName"]),
                age=int(row["age"]),
                home_id=int(row["homeId"]),
                workplace_id=int(row["workplaceId"]) if row["workplaceId"] is not None else None,
                job_title=row["jobTitle"],
                salary_daily=float(row["salaryDaily"]),
                x=int(row["x"]),
                y=int(row["y"]),
                money=float(row["money"]),
                activity=Activity(row["activity"]),
                destination_building_id=(
                    int(row["destinationBuildingId"])
                    if row["destinationBuildingId"] is not None else None
                ),
                planned_activity=Activity(row["plannedActivity"]),
                needs=Needs(
                    hunger=float(needs_row["hunger"]),
                    fatigue=float(needs_row["fatigue"]),
                    stress=float(needs_row["stress"]),
                    social=float(needs_row["social"]),
                ),
                last_decision_reason=str(row["lastDecisionReason"]),
                minutes_late_today=int(row["minutesLateToday"]),
                household_id=int(row["householdId"]) if row.get("householdId") is not None else None,
                sociability=float(row.get("sociability", 50.0)),
                agreeableness=float(row.get("agreeableness", 50.0)),
                spontaneity=float(row.get("spontaneity", 50.0)),
                aggression=float(row.get("aggression", 25.0)),
                impulsivity=float(row.get("impulsivity", 30.0)),
                grudge_tendency=float(row.get("grudgeTendency", 30.0)),
                favorite_place_visits={
                    int(key): int(value) for key, value in row.get("favoritePlaceVisits", {}).items()
                },
                social_event_id=(
                    int(row["socialEventId"]) if row.get("socialEventId") is not None else None
                ),
                social_interactions_today=int(row.get("socialInteractionsToday", 0)),
                invitations_sent=int(row.get("invitationsSent", 0)),
                invitations_accepted=int(row.get("invitationsAccepted", 0)),
                owned_vehicle_id=(
                    int(row.get("ownedVehicleId")) if row.get("ownedVehicleId") is not None else None
                ),
                transport_mode=TransportMode(row.get("transportMode", "walk")),
                last_transport_mode=TransportMode(row.get("lastTransportMode", "walk")),
                travel_stage=TravelStage(row.get("travelStage", "idle")),
                route=[(int(cell[0]), int(cell[1])) for cell in row.get("route", [])],
                route_index=int(row.get("routeIndex", 0)),
                active_vehicle_id=(
                    int(row.get("activeVehicleId")) if row.get("activeVehicleId") is not None else None
                ),
                origin_stop_id=(int(row.get("originStopId")) if row.get("originStopId") is not None else None),
                destination_stop_id=(
                    int(row.get("destinationStopId")) if row.get("destinationStopId") is not None else None
                ),
                waiting_since_tick=(
                    int(row.get("waitingSinceTick")) if row.get("waitingSinceTick") is not None else None
                ),
                trip_started_tick=(
                    int(row.get("tripStartedTick")) if row.get("tripStartedTick") is not None else None
                ),
                trip_distance=int(row.get("tripDistance", 0)),
                last_trip_minutes=int(row.get("lastTripMinutes", 0)),
                travel_minutes_today=int(row.get("travelMinutesToday", 0)),
                trips_today=int(row.get("tripsToday", 0)),
                health=float(row.get("health", 100.0)),
                offenses_committed=int(row.get("offensesCommitted", 0)),
                victimizations=int(row.get("victimizations", 0)),
                arrests=int(row.get("arrests", 0)),
                detained_until_tick=(
                    int(row["detainedUntilTick"])
                    if row.get("detainedUntilTick") is not None else None
                ),
                active_case_ids=[int(value) for value in row.get("activeCaseIds", [])],
                work_start_hour=int(row.get("workStartHour", 8)),
                work_end_hour=int(row.get("workEndHour", 17)),
                work_days=tuple(int(value) for value in row.get("workDays", [1, 2, 3, 4, 5])),
                minutes_worked_today=int(row.get("minutesWorkedToday", 0)),
                shifts_completed=int(row.get("shiftsCompleted", 0)),
                missed_shifts=int(row.get("missedShifts", 0)),
                job_performance=float(row.get("jobPerformance", 65.0)),
                job_satisfaction=float(row.get("jobSatisfaction", 55.0)),
                last_paid_day=int(row.get("lastPaidDay", 0)),
                employed_since_tick=int(row.get("employedSinceTick", 0)),
                job_search_active=bool(row.get("jobSearchActive", False)),
                job_search_since_tick=(
                    int(row["jobSearchSinceTick"]) if row.get("jobSearchSinceTick") is not None else None
                ),
                last_job_change_tick=int(row.get("lastJobChangeTick", 0)),
                application_ids=[int(value) for value in row.get("applicationIds", [])],
                employment_history=[
                    EmploymentRecord(
                        tick=int(item["tick"]),
                        event_type=str(item["eventType"]),
                        label=str(item["label"]),
                        building_id=int(item["buildingId"]) if item.get("buildingId") is not None else None,
                        job_title=item.get("jobTitle"),
                        salary_daily=float(item.get("salaryDaily", 0.0)),
                        reason=str(item.get("reason", "")),
                    )
                    for item in row.get("employmentHistory", [])
                ],
                experience_by_job={
                    str(key): float(value) for key, value in row.get("experienceByJob", {}).items()
                },
                income_today=float(row.get("incomeToday", 0.0)),
                expenses_today=float(row.get("expensesToday", 0.0)),
                financial_stress=float(row.get("financialStress", 10.0)),
                overdraft_limit=float(row.get("overdraftLimit", 120.0)),
                food_units=float(row.get("foodUnits", 5.0)),
                goods_units=float(row.get("goodsUnits", 2.0)),
                last_shopping_tick=(int(row["lastShoppingTick"]) if row.get("lastShoppingTick") is not None else None),
                last_meal_tick=(int(row["lastMealTick"]) if row.get("lastMealTick") is not None else None),
                shopping_visits=int(row.get("shoppingVisits", 0)),
                intoxication=float(row.get("intoxication", 0.0)),
                police_history=[
                    PoliceMeasure(
                        tick=int(item["tick"]),
                        incident_id=int(item["incidentId"]),
                        measure_type=str(item["measureType"]),
                        label=str(item["label"]),
                        duration_minutes=int(item.get("durationMinutes", 0)),
                        reason=str(item.get("reason", "")),
                        officer_ids=tuple(int(value) for value in item.get("officerIds", [])),
                    )
                    for item in row.get("policeHistory", [])
                ],
                current_detention_type=row.get("currentDetentionType"),
            )
            citizen.relationships = {
                int(relationship_row["otherId"]): Relationship(
                    other_id=int(relationship_row["otherId"]),
                    familiarity=float(relationship_row["familiarity"]),
                    affection=float(relationship_row["affection"]),
                    trust=float(relationship_row["trust"]),
                    positive_interactions=int(relationship_row.get("positiveInteractions", 0)),
                    negative_interactions=int(relationship_row.get("negativeInteractions", 0)),
                    last_interaction_tick=int(relationship_row.get("lastInteractionTick", 0)),
                    consecutive_negative_interactions=int(
                        relationship_row.get("consecutiveNegativeInteractions", 0)
                    ),
                    conflict_score=float(relationship_row.get("conflictScore", 0.0)),
                    conflict_level=int(relationship_row.get("conflictLevel", 0)),
                    peak_conflict_level=int(
                        relationship_row.get("peakConflictLevel", relationship_row.get("conflictLevel", 0))
                    ),
                    last_conflict_tick=(
                        int(relationship_row["lastConflictTick"])
                        if relationship_row.get("lastConflictTick") is not None else None
                    ),
                    conflict_history=[
                        ConflictRecord(
                            tick=int(history_row["tick"]),
                            level=int(history_row["level"]),
                            label=str(history_row.get("label", "calme")),
                            title=str(history_row["title"]),
                            incident_id=(
                                int(history_row["incidentId"])
                                if history_row.get("incidentId") is not None else None
                            ),
                            building_id=(
                                int(history_row["buildingId"])
                                if history_row.get("buildingId") is not None else None
                            ),
                            role=str(history_row.get("role", "participant")),
                            outcome=history_row.get("outcome"),
                        )
                        for history_row in relationship_row.get("conflictHistory", [])
                    ],
                )
                for relationship_row in row["relationships"]
            }
            world.citizens[citizen.id] = citizen

        if version >= 2:
            world.vehicles = {}
            for row in state.get("vehicles", []):
                vehicle = Vehicle(
                    id=int(row["id"]),
                    vehicle_type=VehicleType(row["vehicleType"]),
                    x=int(row["x"]),
                    y=int(row["y"]),
                    capacity=int(row["capacity"]),
                    status=VehicleStatus(row["status"]),
                    owner_id=int(row["ownerId"]) if row["ownerId"] is not None else None,
                    line_id=int(row["lineId"]) if row["lineId"] is not None else None,
                    passenger_ids={int(value) for value in row["passengerIds"]},
                    route=[(int(cell[0]), int(cell[1])) for cell in row["route"]],
                    route_index=int(row["routeIndex"]),
                    target_building_id=(
                        int(row["targetBuildingId"]) if row["targetBuildingId"] is not None else None
                    ),
                    current_building_id=(
                        int(row["currentBuildingId"]) if row["currentBuildingId"] is not None else None
                    ),
                    delay_minutes=int(row["delayMinutes"]),
                    distance_today=int(row["distanceToday"]),
                    incident_id=int(row["incidentId"]) if row.get("incidentId") is not None else None,
                    service_started_tick=(
                        int(row["serviceStartedTick"])
                        if row.get("serviceStartedTick") is not None else None
                    ),
                    crew_ids={int(value) for value in row.get("crewIds", [])},
                )
                world.vehicles[vehicle.id] = vehicle
        else:
            world.vehicles = generate_vehicles(
                world.citizens,
                world.buildings,
                world.bus_lines[1].route,
                seed=world.seed,
            )
            for citizen in world.citizens.values():
                citizen.travel_stage = TravelStage.IDLE
                citizen.active_vehicle_id = None
                citizen.route = []
                citizen.route_index = 0

        if not any(vehicle.vehicle_type == VehicleType.POLICE for vehicle in world.vehicles.values()):
            station = next(
                building for building in world.buildings.values()
                if building.building_type == BuildingType.POLICE
            )
            next_vehicle_id = max(world.vehicles, default=0) + 1
            for offset in range(2):
                x, y = station.entrance
                world.vehicles[next_vehicle_id + offset] = Vehicle(
                    id=next_vehicle_id + offset,
                    vehicle_type=VehicleType.POLICE,
                    x=x,
                    y=y,
                    capacity=2,
                    status=VehicleStatus.PARKED,
                    current_building_id=station.id,
                )

        if version >= 3:
            world.households = {
                int(row["id"]): Household(
                    id=int(row["id"]),
                    home_id=int(row["homeId"]),
                    member_ids=[int(value) for value in row["memberIds"]],
                    cohesion=float(row["cohesion"]),
                    shared_meals=int(row["sharedMeals"]),
                    conflicts=int(row["conflicts"]),
                    income_today=float(row.get("incomeToday", 0.0)),
                    recurring_expenses_today=float(row.get("recurringExpensesToday", 0.0)),
                    food_expenses_today=float(row.get("foodExpensesToday", 0.0)),
                    goods_expenses_today=float(row.get("goodsExpensesToday", 0.0)),
                    total_income=float(row.get("totalIncome", 0.0)),
                    total_expenses=float(row.get("totalExpenses", 0.0)),
                    debt=float(row.get("debt", 0.0)),
                    overdraft_limit=float(row.get("overdraftLimit", 240.0)),
                    financial_stress=float(row.get("financialStress", 10.0)),
                    food_budget_daily=float(row.get("foodBudgetDaily", 28.0)),
                    goods_budget_daily=float(row.get("goodsBudgetDaily", 12.0)),
                    financial_history=[
                        HouseholdFinancialRecord(
                            day=int(item["day"]),
                            income=float(item["income"]),
                            recurring_expenses=float(item["recurringExpenses"]),
                            food_expenses=float(item["foodExpenses"]),
                            goods_expenses=float(item["goodsExpenses"]),
                            debt=float(item["debt"]),
                            financial_stress=float(item["financialStress"]),
                        )
                        for item in row.get("financialHistory", [])
                    ],
                )
                for row in state.get("households", [])
            }
            world.social_events = {
                int(row["id"]): SocialEvent(
                    id=int(row["id"]),
                    event_type=SocialEventType(row["eventType"]),
                    host_id=int(row["hostId"]),
                    guest_ids=[int(value) for value in row["guestIds"]],
                    accepted_ids=[int(value) for value in row["acceptedIds"]],
                    declined_ids=[int(value) for value in row["declinedIds"]],
                    building_id=int(row["buildingId"]),
                    planned_tick=int(row["plannedTick"]),
                    duration_minutes=int(row["durationMinutes"]),
                    status=SocialEventStatus(row["status"]),
                    started_tick=int(row["startedTick"]) if row["startedTick"] is not None else None,
                    completed_tick=(
                        int(row["completedTick"]) if row["completedTick"] is not None else None
                    ),
                )
                for row in state.get("socialEvents", [])
            }
        else:
            # Migration des sauvegardes antérieures : les foyers, personnalités et
            # premiers liens sociaux sont générés avec une graine séparée.
            world.households = generate_households(world.citizens, world.buildings, seed=world.seed)
            world.social_events = {}
            world._next_social_event_id = 1

        world.incidents = {}
        if version >= 4:
            world.incidents = {
                int(row["id"]): Incident(
                    id=int(row["id"]),
                    incident_type=str(row["incidentType"]),
                    title=str(row["title"]),
                    description=str(row["description"]),
                    severity=str(row["severity"]),
                    citizen_ids=tuple(int(value) for value in row["citizenIds"]),
                    offender_id=int(row["offenderId"]) if row["offenderId"] is not None else None,
                    victim_ids=tuple(int(value) for value in row["victimIds"]),
                    witness_ids=tuple(int(value) for value in row["witnessIds"]),
                    building_id=int(row["buildingId"]) if row["buildingId"] is not None else None,
                    vehicle_id=int(row["vehicleId"]) if row["vehicleId"] is not None else None,
                    x=int(row["x"]),
                    y=int(row["y"]),
                    created_tick=int(row["createdTick"]),
                    expires_tick=int(row["expiresTick"]),
                    status=IncidentStatus(row["status"]),
                    reported=bool(row["reported"]),
                    police_vehicle_id=(
                        int(row["policeVehicleId"])
                        if row["policeVehicleId"] is not None else None
                    ),
                    dispatched_tick=(
                        int(row["dispatchedTick"]) if row["dispatchedTick"] is not None else None
                    ),
                    police_arrival_tick=(
                        int(row["policeArrivalTick"])
                        if row["policeArrivalTick"] is not None else None
                    ),
                    resolved_tick=(
                        int(row["resolvedTick"]) if row["resolvedTick"] is not None else None
                    ),
                    resolution=row.get("resolution"),
                    conflict_level=int(row.get("conflictLevel", 0)),
                    investigation_id=(
                        int(row["investigationId"])
                        if row.get("investigationId") is not None else None
                    ),
                    police_action=row.get("policeAction"),
                    police_officer_ids=tuple(int(value) for value in row.get("policeOfficerIds", [])),
                    detained_ids=tuple(int(value) for value in row.get("detainedIds", [])),
                )
                for row in state.get("incidents", [])
            }
        world._next_incident_id = max(
            world._next_incident_id,
            max(world.incidents, default=0) + 1,
        )

        if version < 5:
            temperament_rng = random.Random(world.seed ^ 0xC0F11C7)
            for citizen in world.citizens.values():
                citizen.aggression = temperament_rng.triangular(4.0, 72.0, 22.0)
                citizen.impulsivity = temperament_rng.triangular(8.0, 88.0, 34.0)
                citizen.grudge_tendency = temperament_rng.triangular(5.0, 82.0, 28.0)
                if temperament_rng.random() < 0.12:
                    citizen.aggression = temperament_rng.uniform(68.0, 94.0)
                    citizen.impulsivity = temperament_rng.uniform(62.0, 96.0)
                    citizen.grudge_tendency = temperament_rng.uniform(52.0, 91.0)
                    citizen.agreeableness = min(citizen.agreeableness, temperament_rng.uniform(12.0, 42.0))
            for incident in world.incidents.values():
                if incident.conflict_level <= 0 or len(incident.citizen_ids) < 2:
                    continue
                a_id, b_id = incident.citizen_ids[:2]
                if a_id not in world.citizens or b_id not in world.citizens:
                    continue
                for citizen_id, other_id in ((a_id, b_id), (b_id, a_id)):
                    relation = world.citizens[citizen_id].relationships.setdefault(
                        other_id, Relationship(other_id=other_id)
                    )
                    role = (
                        "auteur" if incident.offender_id == citizen_id
                        else "victime" if incident.offender_id == other_id
                        else "participant"
                    )
                    relation.conflict_history.append(
                        ConflictRecord(
                            tick=incident.created_tick,
                            level=incident.conflict_level,
                            label=conflict_label(relation),
                            title=incident.title,
                            incident_id=incident.id,
                            building_id=incident.building_id,
                            role=role,
                            outcome=incident.resolution,
                        )
                    )
                    relation.last_conflict_tick = incident.created_tick
                    relation.peak_conflict_level = max(
                        relation.peak_conflict_level, incident.conflict_level
                    )

        world.evidence = {}
        world.investigations = {}
        world.judicial_cases = {}
        if version >= 5:
            world.evidence = {
                int(row["id"]): Evidence(
                    id=int(row["id"]),
                    investigation_id=int(row["investigationId"]),
                    evidence_type=str(row["evidenceType"]),
                    description=str(row["description"]),
                    reliability=float(row["reliability"]),
                    citizen_id=(int(row["citizenId"]) if row.get("citizenId") is not None else None),
                    created_tick=int(row.get("createdTick", 0)),
                )
                for row in state.get("evidence", [])
            }
            world.investigations = {
                int(row["id"]): Investigation(
                    id=int(row["id"]),
                    incident_id=int(row["incidentId"]),
                    status=InvestigationStatus(row["status"]),
                    opened_tick=int(row["openedTick"]),
                    updated_tick=int(row["updatedTick"]),
                    suspect_ids=[int(value) for value in row.get("suspectIds", [])],
                    lead_suspect_id=(
                        int(row["leadSuspectId"])
                        if row.get("leadSuspectId") is not None else None
                    ),
                    evidence_ids=[int(value) for value in row.get("evidenceIds", [])],
                    confidence=float(row.get("confidence", 0.0)),
                    arrest_tick=(int(row["arrestTick"]) if row.get("arrestTick") is not None else None),
                    case_id=(int(row["caseId"]) if row.get("caseId") is not None else None),
                    notes=[str(value) for value in row.get("notes", [])],
                )
                for row in state.get("investigations", [])
            }
            world.judicial_cases = {
                int(row["id"]): JudicialCase(
                    id=int(row["id"]),
                    investigation_id=int(row["investigationId"]),
                    incident_id=int(row["incidentId"]),
                    defendant_id=int(row["defendantId"]),
                    charges=[str(value) for value in row.get("charges", [])],
                    status=JudicialCaseStatus(row["status"]),
                    filed_tick=int(row["filedTick"]),
                    hearing_tick=int(row["hearingTick"]),
                    evidence_score=float(row.get("evidenceScore", 0.0)),
                    decided_tick=(int(row["decidedTick"]) if row.get("decidedTick") is not None else None),
                    verdict=row.get("verdict"),
                    sentence=row.get("sentence"),
                )
                for row in state.get("judicialCases", [])
            }
        world._next_evidence_id = max(world._next_evidence_id, max(world.evidence, default=0) + 1)
        world._next_investigation_id = max(
            world._next_investigation_id, max(world.investigations, default=0) + 1
        )
        world._next_case_id = max(world._next_case_id, max(world.judicial_cases, default=0) + 1)

        world.job_applications = {
            int(row["id"]): JobApplication(
                id=int(row["id"]),
                citizen_id=int(row["citizenId"]),
                building_id=int(row["buildingId"]),
                job_title=str(row["jobTitle"]),
                salary_daily=float(row["salaryDaily"]),
                submitted_tick=int(row["submittedTick"]),
                score=float(row["score"]),
                status=JobApplicationStatus(row["status"]),
                resolved_tick=int(row["resolvedTick"]) if row.get("resolvedTick") is not None else None,
                reason=row.get("reason"),
            )
            for row in state.get("jobApplications", [])
        }
        world._next_job_application_id = max(
            world._next_job_application_id, max(world.job_applications, default=0) + 1
        )

        world.events = [
            DomainEvent(
                id=int(row["id"]),
                tick=int(row["tick"]),
                day=int(row["day"]),
                hour=int(row["hour"]),
                minute=int(row["minute"]),
                event_type=str(row["eventType"]),
                message=str(row["message"]),
                citizen_ids=tuple(int(value) for value in row["citizenIds"]),
                building_id=int(row["buildingId"]) if row["buildingId"] is not None else None,
                vehicle_id=int(row["vehicleId"]) if row.get("vehicleId") is not None else None,
                severity=str(row["severity"]),
                incident_id=int(row["incidentId"]) if row.get("incidentId") is not None else None,
            )
            for row in state["events"]
        ]
        return world

    @staticmethod
    def _nested_tuple(value: Any) -> Any:
        if isinstance(value, list):
            return tuple(World._nested_tuple(item) for item in value)
        return value

    def _citizen_summary(self, citizen: Citizen) -> dict[str, Any]:
        return {
            "id": citizen.id,
            "name": citizen.full_name,
            "x": citizen.x,
            "y": citizen.y,
            "activity": citizen.activity.value,
            "destinationBuildingId": citizen.destination_building_id,
            "transportMode": citizen.transport_mode.value,
            "travelStage": citizen.travel_stage.value,
            "activeVehicleId": citizen.active_vehicle_id,
            "socialEventId": citizen.social_event_id,
            "friendCount": sum(
                1 for relationship in citizen.relationships.values()
                if relationship_label(relationship) in {"friend", "close_friend"}
            ),
            "jobTitle": citizen.job_title,
            "onDuty": is_on_duty(self, citizen),
        }

    def _building_to_dict(self, building: Building) -> dict[str, Any]:
        return {
            "id": building.id,
            "name": building.name,
            "type": building.building_type.value,
            "x": building.x,
            "y": building.y,
            "width": building.width,
            "height": building.height,
            "capacity": building.capacity,
            "occupancy": len(building.occupants),
            "employeesRequired": building.employees_required,
            "staffOnDuty": staff_count(self, building.id),
            "operational": building_operational(self, building.id),
            "foodStock": round(building.food_stock, 1),
            "goodsStock": round(building.goods_stock, 1),
            "revenueToday": round(building.revenue_today, 2),
            "cash": round(building.cash, 2),
            "payrollToday": round(building.payroll_today, 2),
            "fixedCostsToday": round(building.fixed_costs_today, 2),
            "resultToday": round(building.result_today, 2),
            "serviceLevel": round(building.service_level, 1),
            "businessStatus": building.business_status.value,
            "assignedEmployees": assigned_staff_count(self, building.id),
            "employeeCapacity": building.employee_capacity,
            "targetEmployees": building.target_employees,
            "openPositions": building.open_positions,
        }

    @staticmethod
    def _vehicle_summary(vehicle: Vehicle) -> dict[str, Any]:
        return {
            "id": vehicle.id,
            "type": vehicle.vehicle_type.value,
            "x": vehicle.x,
            "y": vehicle.y,
            "status": vehicle.status.value,
            "occupancy": len(vehicle.passenger_ids),
            "capacity": vehicle.capacity,
            "ownerId": vehicle.owner_id,
            "lineId": vehicle.line_id,
            "crewIds": sorted(vehicle.crew_ids),
        }

    @staticmethod
    def _bus_stop_to_dict(stop: BusStop) -> dict[str, Any]:
        return {
            "id": stop.id,
            "name": stop.name,
            "x": stop.x,
            "y": stop.y,
            "lineId": stop.line_id,
            "sequence": stop.sequence,
        }

    @staticmethod
    def _bus_line_to_dict(line: BusLine) -> dict[str, Any]:
        return {
            "id": line.id,
            "name": line.name,
            "stopIds": line.stop_ids,
            "route": [{"x": x, "y": y} for x, y in line.route],
            "fare": line.fare,
        }

    def _social_event_to_dict(self, event: SocialEvent) -> dict[str, Any]:
        building = self.buildings[event.building_id]
        return {
            "id": event.id,
            "type": event.event_type.value,
            "status": event.status.value,
            "host": {"id": event.host_id, "name": self.citizens[event.host_id].full_name},
            "participants": [
                {"id": citizen_id, "name": self.citizens[citizen_id].full_name}
                for citizen_id in event.participant_ids
            ],
            "building": {"id": building.id, "name": building.name},
            "plannedTick": event.planned_tick,
            "minutesUntilStart": max(0, event.planned_tick - self.tick),
            "durationMinutes": event.duration_minutes,
        }

    def _household_summary(self, household: Household) -> dict[str, Any]:
        home = self.buildings[household.home_id]
        return {
            "id": household.id,
            "homeId": household.home_id,
            "homeName": home.name,
            "members": len(household.member_ids),
            "cohesion": round(household.cohesion, 1),
            "sharedMeals": household.shared_meals,
            "conflicts": household.conflicts,
            "incomeToday": round(household.income_today, 2),
            "expensesToday": round(household.recurring_expenses_today + household.food_expenses_today + household.goods_expenses_today, 2),
            "debt": round(household.debt, 2),
            "financialStress": round(household.financial_stress, 1),
        }

    def _incident_summary(self, incident: Incident) -> dict[str, Any]:
        return {
            "id": incident.id,
            "type": incident.incident_type,
            "title": incident.title,
            "severity": incident.severity,
            "status": incident.status.value,
            "x": incident.x,
            "y": incident.y,
            "buildingId": incident.building_id,
            "vehicleId": incident.vehicle_id,
            "citizenIds": list(incident.citizen_ids),
            "reported": incident.reported,
            "policeVehicleId": incident.police_vehicle_id,
            "createdTick": incident.created_tick,
            "remainingMinutes": max(0, incident.expires_tick - self.tick),
            "conflictLevel": incident.conflict_level,
            "investigationId": incident.investigation_id,
            "policeAction": incident.police_action,
            "policeOfficerIds": list(incident.police_officer_ids),
            "detainedIds": list(incident.detained_ids),
        }

    def _job_application_to_dict(self, application: JobApplication) -> dict[str, Any]:
        building = self.buildings[application.building_id]
        return {
            "id": application.id,
            "citizenId": application.citizen_id,
            "building": {"id": building.id, "name": building.name},
            "jobTitle": application.job_title,
            "salaryDaily": application.salary_daily,
            "submittedTick": application.submitted_tick,
            "score": round(application.score, 1),
            "status": application.status.value,
            "resolvedTick": application.resolved_tick,
            "reason": application.reason,
        }

    @staticmethod
    def _employment_record_to_dict(record: EmploymentRecord) -> dict[str, Any]:
        return {
            "tick": record.tick,
            "eventType": record.event_type,
            "label": record.label,
            "buildingId": record.building_id,
            "jobTitle": record.job_title,
            "salaryDaily": record.salary_daily,
            "reason": record.reason,
        }

    @staticmethod
    def _business_financial_to_dict(record: BusinessFinancialRecord) -> dict[str, Any]:
        return {
            "day": record.day,
            "revenue": round(record.revenue, 2),
            "payroll": round(record.payroll, 2),
            "fixedCosts": round(record.fixed_costs, 2),
            "result": round(record.result, 2),
            "cash": round(record.cash, 2),
            "serviceLevel": round(record.service_level, 1),
            "status": record.status.value,
        }

    @staticmethod
    def _household_financial_to_dict(record: HouseholdFinancialRecord) -> dict[str, Any]:
        return {
            "day": record.day,
            "income": round(record.income, 2),
            "recurringExpenses": round(record.recurring_expenses, 2),
            "foodExpenses": round(record.food_expenses, 2),
            "goodsExpenses": round(record.goods_expenses, 2),
            "debt": round(record.debt, 2),
            "financialStress": round(record.financial_stress, 1),
        }

    @staticmethod
    def _event_to_dict(event: DomainEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "tick": event.tick,
            "day": event.day,
            "hour": event.hour,
            "minute": event.minute,
            "time": f"J{event.day} {event.hour:02d}:{event.minute:02d}",
            "eventType": event.event_type,
            "message": event.message,
            "citizenIds": list(event.citizen_ids),
            "buildingId": event.building_id,
            "vehicleId": event.vehicle_id,
            "severity": event.severity,
            "incidentId": event.incident_id,
        }

    @staticmethod
    def _export_building(building: Building) -> dict[str, Any]:
        return {
            "id": building.id,
            "name": building.name,
            "buildingType": building.building_type.value,
            "x": building.x,
            "y": building.y,
            "width": building.width,
            "height": building.height,
            "capacity": building.capacity,
            "occupants": sorted(building.occupants),
            "employeesRequired": building.employees_required,
            "foodStock": building.food_stock,
            "goodsStock": building.goods_stock,
            "revenueToday": building.revenue_today,
            "cash": building.cash,
            "totalRevenue": building.total_revenue,
            "payrollToday": building.payroll_today,
            "fixedCostsToday": building.fixed_costs_today,
            "resultToday": building.result_today,
            "fixedCostDaily": building.fixed_cost_daily,
            "employeeCapacity": building.employee_capacity,
            "targetEmployees": building.target_employees,
            "openPositions": building.open_positions,
            "serviceLevel": building.service_level,
            "businessStatus": building.business_status.value,
            "deficitDays": building.deficit_days,
            "productiveMinutesToday": building.productive_minutes_today,
            "financialHistory": [
                {
                    "day": item.day,
                    "revenue": item.revenue,
                    "payroll": item.payroll,
                    "fixedCosts": item.fixed_costs,
                    "result": item.result,
                    "cash": item.cash,
                    "serviceLevel": item.service_level,
                    "status": item.status.value,
                }
                for item in building.financial_history
            ],
            "employmentEvents": [
                World._export_employment_record(item) for item in building.employment_events
            ],
        }

    @staticmethod
    def _export_citizen(citizen: Citizen) -> dict[str, Any]:
        return {
            "id": citizen.id,
            "firstName": citizen.first_name,
            "lastName": citizen.last_name,
            "age": citizen.age,
            "homeId": citizen.home_id,
            "workplaceId": citizen.workplace_id,
            "jobTitle": citizen.job_title,
            "salaryDaily": citizen.salary_daily,
            "x": citizen.x,
            "y": citizen.y,
            "money": citizen.money,
            "activity": citizen.activity.value,
            "destinationBuildingId": citizen.destination_building_id,
            "plannedActivity": citizen.planned_activity.value,
            "needs": {
                "hunger": citizen.needs.hunger,
                "fatigue": citizen.needs.fatigue,
                "stress": citizen.needs.stress,
                "social": citizen.needs.social,
            },
            "relationships": [
                {
                    "otherId": relationship.other_id,
                    "familiarity": relationship.familiarity,
                    "affection": relationship.affection,
                    "trust": relationship.trust,
                    "positiveInteractions": relationship.positive_interactions,
                    "negativeInteractions": relationship.negative_interactions,
                    "lastInteractionTick": relationship.last_interaction_tick,
                    "consecutiveNegativeInteractions": relationship.consecutive_negative_interactions,
                    "conflictScore": relationship.conflict_score,
                    "conflictLevel": relationship.conflict_level,
                    "conflictLabel": conflict_label(relationship),
                    "peakConflictLevel": relationship.peak_conflict_level,
                    "lastConflictTick": relationship.last_conflict_tick,
                    "conflictHistory": [
                        {
                            "tick": record.tick,
                            "level": record.level,
                            "label": record.label,
                            "title": record.title,
                            "incidentId": record.incident_id,
                            "buildingId": record.building_id,
                            "role": record.role,
                            "outcome": record.outcome,
                        }
                        for record in relationship.conflict_history
                    ],
                }
                for relationship in citizen.relationships.values()
            ],
            "lastDecisionReason": citizen.last_decision_reason,
            "minutesLateToday": citizen.minutes_late_today,
            "householdId": citizen.household_id,
            "sociability": citizen.sociability,
            "agreeableness": citizen.agreeableness,
            "spontaneity": citizen.spontaneity,
            "aggression": citizen.aggression,
            "impulsivity": citizen.impulsivity,
            "grudgeTendency": citizen.grudge_tendency,
            "favoritePlaceVisits": {str(key): value for key, value in citizen.favorite_place_visits.items()},
            "socialEventId": citizen.social_event_id,
            "socialInteractionsToday": citizen.social_interactions_today,
            "invitationsSent": citizen.invitations_sent,
            "invitationsAccepted": citizen.invitations_accepted,
            "ownedVehicleId": citizen.owned_vehicle_id,
            "transportMode": citizen.transport_mode.value,
            "lastTransportMode": citizen.last_transport_mode.value,
            "travelStage": citizen.travel_stage.value,
            "route": [list(cell) for cell in citizen.route],
            "routeIndex": citizen.route_index,
            "activeVehicleId": citizen.active_vehicle_id,
            "originStopId": citizen.origin_stop_id,
            "destinationStopId": citizen.destination_stop_id,
            "waitingSinceTick": citizen.waiting_since_tick,
            "tripStartedTick": citizen.trip_started_tick,
            "tripDistance": citizen.trip_distance,
            "lastTripMinutes": citizen.last_trip_minutes,
            "travelMinutesToday": citizen.travel_minutes_today,
            "tripsToday": citizen.trips_today,
            "health": citizen.health,
            "offensesCommitted": citizen.offenses_committed,
            "victimizations": citizen.victimizations,
            "arrests": citizen.arrests,
            "detainedUntilTick": citizen.detained_until_tick,
            "activeCaseIds": list(citizen.active_case_ids),
            "workStartHour": citizen.work_start_hour,
            "workEndHour": citizen.work_end_hour,
            "workDays": list(citizen.work_days),
            "minutesWorkedToday": citizen.minutes_worked_today,
            "shiftsCompleted": citizen.shifts_completed,
            "missedShifts": citizen.missed_shifts,
            "jobPerformance": citizen.job_performance,
            "jobSatisfaction": citizen.job_satisfaction,
            "lastPaidDay": citizen.last_paid_day,
            "employedSinceTick": citizen.employed_since_tick,
            "jobSearchActive": citizen.job_search_active,
            "jobSearchSinceTick": citizen.job_search_since_tick,
            "lastJobChangeTick": citizen.last_job_change_tick,
            "applicationIds": list(citizen.application_ids),
            "employmentHistory": [
                World._export_employment_record(item) for item in citizen.employment_history
            ],
            "experienceByJob": dict(citizen.experience_by_job),
            "incomeToday": citizen.income_today,
            "expensesToday": citizen.expenses_today,
            "financialStress": citizen.financial_stress,
            "overdraftLimit": citizen.overdraft_limit,
            "foodUnits": citizen.food_units,
            "goodsUnits": citizen.goods_units,
            "lastShoppingTick": citizen.last_shopping_tick,
            "lastMealTick": citizen.last_meal_tick,
            "shoppingVisits": citizen.shopping_visits,
            "intoxication": citizen.intoxication,
            "policeHistory": [
                {
                    "tick": item.tick,
                    "incidentId": item.incident_id,
                    "measureType": item.measure_type,
                    "label": item.label,
                    "durationMinutes": item.duration_minutes,
                    "reason": item.reason,
                    "officerIds": list(item.officer_ids),
                }
                for item in citizen.police_history
            ],
            "currentDetentionType": citizen.current_detention_type,
        }

    @staticmethod
    def _export_household(household: Household) -> dict[str, Any]:
        return {
            "id": household.id,
            "homeId": household.home_id,
            "memberIds": list(household.member_ids),
            "cohesion": household.cohesion,
            "sharedMeals": household.shared_meals,
            "conflicts": household.conflicts,
            "incomeToday": household.income_today,
            "recurringExpensesToday": household.recurring_expenses_today,
            "foodExpensesToday": household.food_expenses_today,
            "goodsExpensesToday": household.goods_expenses_today,
            "totalIncome": household.total_income,
            "totalExpenses": household.total_expenses,
            "debt": household.debt,
            "overdraftLimit": household.overdraft_limit,
            "financialStress": household.financial_stress,
            "foodBudgetDaily": household.food_budget_daily,
            "goodsBudgetDaily": household.goods_budget_daily,
            "financialHistory": [
                {
                    "day": item.day,
                    "income": item.income,
                    "recurringExpenses": item.recurring_expenses,
                    "foodExpenses": item.food_expenses,
                    "goodsExpenses": item.goods_expenses,
                    "debt": item.debt,
                    "financialStress": item.financial_stress,
                }
                for item in household.financial_history
            ],
        }

    @staticmethod
    def _export_social_event(event: SocialEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "eventType": event.event_type.value,
            "hostId": event.host_id,
            "guestIds": list(event.guest_ids),
            "acceptedIds": list(event.accepted_ids),
            "declinedIds": list(event.declined_ids),
            "buildingId": event.building_id,
            "plannedTick": event.planned_tick,
            "durationMinutes": event.duration_minutes,
            "status": event.status.value,
            "startedTick": event.started_tick,
            "completedTick": event.completed_tick,
        }

    @staticmethod
    def _export_vehicle(vehicle: Vehicle) -> dict[str, Any]:
        return {
            "id": vehicle.id,
            "vehicleType": vehicle.vehicle_type.value,
            "x": vehicle.x,
            "y": vehicle.y,
            "capacity": vehicle.capacity,
            "status": vehicle.status.value,
            "ownerId": vehicle.owner_id,
            "lineId": vehicle.line_id,
            "passengerIds": sorted(vehicle.passenger_ids),
            "route": [list(cell) for cell in vehicle.route],
            "routeIndex": vehicle.route_index,
            "targetBuildingId": vehicle.target_building_id,
            "currentBuildingId": vehicle.current_building_id,
            "delayMinutes": vehicle.delay_minutes,
            "distanceToday": vehicle.distance_today,
            "incidentId": vehicle.incident_id,
            "serviceStartedTick": vehicle.service_started_tick,
            "crewIds": sorted(vehicle.crew_ids),
        }

    @staticmethod
    def _export_incident(incident: Incident) -> dict[str, Any]:
        return {
            "id": incident.id,
            "incidentType": incident.incident_type,
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity,
            "citizenIds": list(incident.citizen_ids),
            "offenderId": incident.offender_id,
            "victimIds": list(incident.victim_ids),
            "witnessIds": list(incident.witness_ids),
            "buildingId": incident.building_id,
            "vehicleId": incident.vehicle_id,
            "x": incident.x,
            "y": incident.y,
            "createdTick": incident.created_tick,
            "expiresTick": incident.expires_tick,
            "status": incident.status.value,
            "reported": incident.reported,
            "policeVehicleId": incident.police_vehicle_id,
            "dispatchedTick": incident.dispatched_tick,
            "policeArrivalTick": incident.police_arrival_tick,
            "resolvedTick": incident.resolved_tick,
            "resolution": incident.resolution,
            "conflictLevel": incident.conflict_level,
            "investigationId": incident.investigation_id,
        }

    @staticmethod
    def _export_evidence(item: Evidence) -> dict[str, Any]:
        return {
            "id": item.id,
            "investigationId": item.investigation_id,
            "evidenceType": item.evidence_type,
            "description": item.description,
            "reliability": item.reliability,
            "citizenId": item.citizen_id,
            "createdTick": item.created_tick,
        }

    @staticmethod
    def _export_investigation(item: Investigation) -> dict[str, Any]:
        return {
            "id": item.id,
            "incidentId": item.incident_id,
            "status": item.status.value,
            "openedTick": item.opened_tick,
            "updatedTick": item.updated_tick,
            "suspectIds": list(item.suspect_ids),
            "leadSuspectId": item.lead_suspect_id,
            "evidenceIds": list(item.evidence_ids),
            "confidence": item.confidence,
            "arrestTick": item.arrest_tick,
            "caseId": item.case_id,
            "notes": list(item.notes),
        }

    @staticmethod
    def _export_case(item: JudicialCase) -> dict[str, Any]:
        return {
            "id": item.id,
            "investigationId": item.investigation_id,
            "incidentId": item.incident_id,
            "defendantId": item.defendant_id,
            "charges": list(item.charges),
            "status": item.status.value,
            "filedTick": item.filed_tick,
            "hearingTick": item.hearing_tick,
            "evidenceScore": item.evidence_score,
            "decidedTick": item.decided_tick,
            "verdict": item.verdict,
            "sentence": item.sentence,
        }

    @staticmethod
    def _export_job_application(item: JobApplication) -> dict[str, Any]:
        return {
            "id": item.id,
            "citizenId": item.citizen_id,
            "buildingId": item.building_id,
            "jobTitle": item.job_title,
            "salaryDaily": item.salary_daily,
            "submittedTick": item.submitted_tick,
            "score": item.score,
            "status": item.status.value,
            "resolvedTick": item.resolved_tick,
            "reason": item.reason,
        }

    @staticmethod
    def _export_employment_record(item: EmploymentRecord) -> dict[str, Any]:
        return {
            "tick": item.tick,
            "eventType": item.event_type,
            "label": item.label,
            "buildingId": item.building_id,
            "jobTitle": item.job_title,
            "salaryDaily": item.salary_daily,
            "reason": item.reason,
        }

    @staticmethod
    def _export_event(event: DomainEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "tick": event.tick,
            "day": event.day,
            "hour": event.hour,
            "minute": event.minute,
            "eventType": event.event_type,
            "message": event.message,
            "citizenIds": list(event.citizen_ids),
            "buildingId": event.building_id,
            "vehicleId": event.vehicle_id,
            "severity": event.severity,
            "incidentId": event.incident_id,
        }
