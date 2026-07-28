from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from .economy import economy_metrics, economy_overview
from .health import health_metrics, health_overview
from .models import (
    BuildingType,
    IncidentStatus,
    InvestigationStatus,
    JudicialCaseStatus,
    SocialEventStatus,
    TransportMode,
    TravelStage,
    VehicleStatus,
    VehicleType,
)
from .social import friendship_counts
from .work import building_operational, is_on_duty

if TYPE_CHECKING:
    from .world import World


def build_dynamic_snapshot(world: World) -> dict[str, Any]:
    """Serialize only state that can change while the simulation is running."""
    activity_counts = Counter(citizen.activity.value for citizen in world.citizens.values())
    transport_mode_counts = Counter(
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
    buses = [vehicle for vehicle in world.vehicles.values() if vehicle.vehicle_type == VehicleType.BUS]
    completed_trip_times = [
        citizen.last_trip_minutes for citizen in world.citizens.values() if citizen.last_trip_minutes
    ]
    friendships, rivalries, isolated, average_network = friendship_counts(world)
    active_social_events = [
        event
        for event in world.social_events.values()
        if event.status in {SocialEventStatus.PLANNED, SocialEventStatus.ACTIVE}
    ]
    active_incidents = [
        incident
        for incident in world.incidents.values()
        if incident.status != IncidentStatus.EXPIRED and world.tick < incident.expires_tick
    ]
    police_units = [
        vehicle for vehicle in world.vehicles.values() if vehicle.vehicle_type == VehicleType.POLICE
    ]
    response_times = [
        incident.police_arrival_tick - incident.dispatched_tick
        for incident in world.incidents.values()
        if incident.police_arrival_tick is not None and incident.dispatched_tick is not None
    ]
    open_investigations = [
        investigation
        for investigation in world.investigations.values()
        if investigation.status in {InvestigationStatus.OPEN, InvestigationStatus.SUSPECT_IDENTIFIED}
    ]
    awaiting_cases = [
        case
        for case in world.judicial_cases.values()
        if case.status == JudicialCaseStatus.AWAITING_HEARING
    ]
    market = world._first_building(BuildingType.SHOP)
    employed = [citizen for citizen in world.citizens.values() if citizen.workplace_id is not None]
    on_duty = [citizen for citizen in employed if is_on_duty(world, citizen)]
    police_officers = [
        citizen
        for citizen in employed
        if world.buildings[citizen.workplace_id].building_type == BuildingType.POLICE
    ]
    staffed_patrols = [unit for unit in police_units if len(unit.crew_ids) >= min(2, unit.capacity)]
    operational_workplaces = [
        building
        for building in world.buildings.values()
        if building.building_type not in {BuildingType.HOME, BuildingType.PARK}
        and building_operational(world, building.id)
    ]

    return {
        "tick": world.tick,
        "day": world.day,
        "hour": world.hour,
        "minute": world.minute,
        "timeLabel": world.simulation_time_label,
        "stats": {
            **economy_metrics(world),
            **health_metrics(world),
            "population": len(world.citizens),
            "averageMoney": round(
                sum(citizen.money for citizen in world.citizens.values())
                / max(1, len(world.citizens)),
                2,
            ),
            "reportedIncidents": sum(1 for incident in world.incidents.values() if incident.reported),
            "activeIncidents": len(active_incidents),
            "seriousIncidents": sum(
                1 for incident in active_incidents if incident.severity == "danger"
            ),
            "policeUnitsAvailable": sum(
                1 for unit in staffed_patrols if unit.status == VehicleStatus.PARKED
            ),
            "policeOfficersOnDuty": sum(
                1 for citizen in police_officers if is_on_duty(world, citizen)
            ),
            "staffedPatrols": len(staffed_patrols),
            "policeWarningsToday": world.police_warnings_today,
            "policeDetentionsToday": world.police_detentions_today,
            "policeResponsesToday": world.police_responses_today,
            "averagePoliceResponseMinutes": round(
                sum(response_times) / max(1, len(response_times)), 1
            ),
            "openInvestigations": len(open_investigations),
            "suspectsIdentified": sum(
                1 for investigation in open_investigations
                if investigation.lead_suspect_id is not None
            ),
            "arrestsToday": world.arrests_today,
            "casesFiledToday": world.cases_filed_today,
            "casesAwaitingHearing": len(awaiting_cases),
            "casesDecided": sum(
                1 for case in world.judicial_cases.values()
                if case.status in {JudicialCaseStatus.DECIDED, JudicialCaseStatus.DISMISSED}
            ),
            "employedCitizens": len(employed),
            "workersOnDuty": len(on_duty),
            "operationalWorkplaces": len(operational_workplaces),
            "averageJobPerformance": round(
                sum(citizen.job_performance for citizen in employed) / max(1, len(employed)), 1
            ),
            "shoppingTripsToday": world.shopping_trips_today,
            "shopSalesToday": round(world.shop_sales_today, 2),
            "marketFoodStock": round(market.food_stock, 1) if market else 0.0,
            "marketGoodsStock": round(market.goods_stock, 1) if market else 0.0,
            "activityCounts": dict(activity_counts),
            "transportModeCounts": {
                mode.value: transport_mode_counts.get(mode.value, 0) for mode in TransportMode
            },
            "tripCountsToday": {
                mode.value: world.trip_counts_today.get(mode.value, 0) for mode in TransportMode
            },
            "carOwners": sum(1 for citizen in world.citizens.values() if citizen.owned_vehicle_id),
            "movingVehicles": len(moving_vehicles),
            "busPassengers": sum(len(bus.passenger_ids) for bus in buses),
            "busBoardingsToday": world.bus_boardings_today,
            "trafficDelayToday": world.traffic_delay_today,
            "averageTripMinutes": round(
                sum(completed_trip_times) / max(1, len(completed_trip_times)), 1
            ),
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
            "activeSocialEvents": len(active_social_events),
            "socialGatheringsCompleted": world.social_gatherings_completed,
        },
        "citizens": [world._citizen_summary(citizen) for citizen in world.citizens.values()],
        "buildings": [world._building_to_dict(building) for building in world.buildings.values()],
        "vehicles": [world._vehicle_summary(vehicle) for vehicle in world.vehicles.values()],
        "roads": {"congestion": world._congestion_cells()},
        "transport": {"operating": world.bus_operating},
        "social": {
            "events": [world._social_event_to_dict(event) for event in active_social_events],
            "households": [world._household_summary(household) for household in world.households.values()],
        },
        "economy": economy_overview(world),
        "health": health_overview(world),
        "incidents": [world._incident_summary(incident) for incident in active_incidents],
        "events": [world._event_to_dict(event) for event in world.events[-80:]],
    }
