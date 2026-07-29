from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from .banking import banking_overview
from .communication import communication_metrics
from .crime import crime_overview
from .economy import economy_metrics
from .health import health_metrics
from .housing import housing_metrics
from .justice import justice_metrics
from .neighborhood import neighborhood_city_metrics
from .models import (
    BuildingType,
    IncidentStatus,
    InvestigationStatus,
    JudicialCaseStatus,
    TransportMode,
    TravelStage,
    VehicleStatus,
    VehicleType,
)
from .social import friendship_counts
from .work import building_operational, is_on_duty

if TYPE_CHECKING:
    from .world import World


def population_metrics(world: World) -> dict[str, object]:
    citizens = list(world.citizens.values())
    employed = [citizen for citizen in citizens if citizen.workplace_id is not None]
    workplaces = (
        building
        for building in world.buildings.values()
        if building.building_type not in {BuildingType.HOME, BuildingType.PARK}
    )
    return {
        "population": len(citizens),
        "averageMoney": round(sum(citizen.money for citizen in citizens) / max(1, len(citizens)), 2),
        "employedCitizens": len(employed),
        "workersOnDuty": sum(is_on_duty(world, citizen) for citizen in employed),
        "operationalWorkplaces": sum(building_operational(world, building.id) for building in workplaces),
        "averageJobPerformance": round(
            sum(citizen.job_performance for citizen in employed) / max(1, len(employed)), 1
        ),
        "activityCounts": _counts(citizen.activity.value for citizen in citizens),
    }


def safety_metrics(world: World) -> dict[str, object]:
    active_incidents = [
        incident
        for incident in world.incidents.values()
        if incident.status != IncidentStatus.EXPIRED and world.tick < incident.expires_tick
    ]
    staffed_units = [
        vehicle
        for vehicle in world.vehicles.values()
        if vehicle.vehicle_type == VehicleType.POLICE
        and len(vehicle.crew_ids) >= min(2, vehicle.capacity)
    ]
    officers = [
        citizen
        for citizen in world.citizens.values()
        if citizen.workplace_id in world.buildings
        and world.buildings[citizen.workplace_id].building_type == BuildingType.POLICE
    ]
    response_times = [
        incident.police_arrival_tick - incident.dispatched_tick
        for incident in world.incidents.values()
        if incident.police_arrival_tick is not None and incident.dispatched_tick is not None
    ]
    investigations = [
        investigation
        for investigation in world.investigations.values()
        if investigation.status in {
            InvestigationStatus.OPEN,
            InvestigationStatus.SUSPECT_IDENTIFIED,
        }
    ]
    awaiting_hearing = [
        case
        for case in world.judicial_cases.values()
        if case.status == JudicialCaseStatus.AWAITING_HEARING
    ]
    return {
        "reportedIncidents": sum(incident.reported for incident in world.incidents.values()),
        "activeIncidents": len(active_incidents),
        "seriousIncidents": sum(incident.severity == "danger" for incident in active_incidents),
        "policeUnitsAvailable": sum(unit.status in {VehicleStatus.PARKED, VehicleStatus.IN_SERVICE} for unit in staffed_units),
        "policeOfficersOnDuty": sum(is_on_duty(world, officer) for officer in officers),
        "staffedPatrols": len(staffed_units),
        "policeWarningsToday": world.police_warnings_today,
        "policeDetentionsToday": world.police_detentions_today,
        "policeResponsesToday": world.police_responses_today,
        "averagePoliceResponseMinutes": round(
            sum(response_times) / max(1, len(response_times)), 1
        ),
        "openInvestigations": len(investigations),
        "suspectsIdentified": sum(
            investigation.lead_suspect_id is not None for investigation in investigations
        ),
        "arrestsToday": world.arrests_today,
        "casesFiledToday": world.cases_filed_today,
        "casesAwaitingHearing": len(awaiting_hearing),
        "casesDecided": sum(
            case.status in {JudicialCaseStatus.DECIDED, JudicialCaseStatus.DISMISSED}
            for case in world.judicial_cases.values()
        ),
    }


def commerce_metrics(world: World) -> dict[str, object]:
    market = world._first_building(BuildingType.SHOP)
    return {
        "shoppingTripsToday": world.shopping_trips_today,
        "shopSalesToday": round(world.shop_sales_today, 2),
        "marketFoodStock": round(market.food_stock, 1) if market else 0.0,
        "marketGoodsStock": round(market.goods_stock, 1) if market else 0.0,
    }


def mobility_metrics(world: World) -> dict[str, object]:
    transport_counts = _counts(
        citizen.transport_mode.value
        for citizen in world.citizens.values()
        if citizen.travel_stage != TravelStage.IDLE
    )
    moving_vehicles = [
        vehicle
        for vehicle in world.vehicles.values()
        if vehicle.status
        in {
            VehicleStatus.DRIVING,
            VehicleStatus.IN_SERVICE,
            VehicleStatus.RESPONDING,
            VehicleStatus.RETURNING,
        }
    ]
    buses = [
        vehicle for vehicle in world.vehicles.values() if vehicle.vehicle_type == VehicleType.BUS
    ]
    trip_times = [
        citizen.last_trip_minutes
        for citizen in world.citizens.values()
        if citizen.last_trip_minutes
    ]
    return {
        "transportModeCounts": {
            mode.value: transport_counts.get(mode.value, 0) for mode in TransportMode
        },
        "tripCountsToday": {
            mode.value: world.trip_counts_today.get(mode.value, 0) for mode in TransportMode
        },
        "carOwners": sum(citizen.owned_vehicle_id is not None for citizen in world.citizens.values()),
        "movingVehicles": len(moving_vehicles),
        "busPassengers": sum(len(bus.passenger_ids) for bus in buses),
        "busBoardingsToday": world.bus_boardings_today,
        "trafficDelayToday": world.traffic_delay_today,
        "averageTripMinutes": round(sum(trip_times) / max(1, len(trip_times)), 1),
    }


def social_metrics(world: World) -> dict[str, object]:
    friendships, rivalries, isolated, average_network = friendship_counts(world)
    active_events = sum(
        event.status.value in {"planned", "active"} for event in world.social_events.values()
    )
    return {
        "households": len(world.households),
        "averageHouseholdCohesion": round(
            sum(household.cohesion for household in world.households.values())
            / max(1, len(world.households)),
            1,
        ),
        "friendships": friendships,
        "rivalries": rivalries,
        "isolatedCitizens": isolated,
        "averageSocialNetwork": round(average_network, 1),
        "socialInvitationsToday": world.social_invitations_today,
        "socialAcceptancesToday": world.social_acceptances_today,
        "activeSocialEvents": active_events,
        "socialGatheringsCompleted": world.social_gatherings_completed,
    }


def city_metrics(world: World) -> dict[str, object]:
    sections = (
        economy_metrics(world),
        health_metrics(world),
        housing_metrics(world),
        population_metrics(world),
        safety_metrics(world),
        justice_metrics(world),
        commerce_metrics(world),
        mobility_metrics(world),
        social_metrics(world),
        communication_metrics(world),
        neighborhood_city_metrics(world),
        banking_overview(world)["metrics"],
        crime_overview(world)["metrics"],
    )
    return {key: value for section in sections for key, value in section.items()}


def _counts(values: Iterable[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return result