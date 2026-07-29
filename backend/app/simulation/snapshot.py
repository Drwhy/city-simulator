from __future__ import annotations
from typing import TYPE_CHECKING, Any
from .banking import banking_overview
from .communication import communication_overview
from .crime import crime_overview
from .economy import economy_overview
from .health import health_overview
from .housing import housing_overview
from .justice import justice_overview
from .metrics import city_metrics
from .neighborhood import neighborhood_overview
from .models import IncidentStatus, SocialEventStatus
if TYPE_CHECKING:
    from .world import World

def build_dynamic_snapshot(world: World) -> dict[str, Any]:
    """Projection dynamique unique utilisée par le snapshot initial et les deltas."""
    active_social_events=[event for event in world.social_events.values() if event.status in {SocialEventStatus.PLANNED,SocialEventStatus.ACTIVE}]
    active_incidents=[incident for incident in world.incidents.values() if incident.status!=IncidentStatus.EXPIRED and world.tick<incident.expires_tick]
    return {
        "tick":world.tick,"day":world.day,"hour":world.hour,"minute":world.minute,"timeLabel":world.simulation_time_label,
        "stats":city_metrics(world),
        "citizens":[world._citizen_summary(citizen) for citizen in world.citizens.values()],
        "buildings":[world._building_to_dict(building) for building in world.buildings.values()],
        "vehicles":[world._vehicle_summary(vehicle) for vehicle in world.vehicles.values()],
        "roads":{"congestion":world._congestion_cells()},
        "transport":{"operating":world.bus_operating},
        "social":{"events":[world._social_event_to_dict(event) for event in active_social_events],"households":[world._household_summary(household) for household in world.households.values()]},
        "economy":economy_overview(world),"banking":banking_overview(world),"crime":crime_overview(world),"health":health_overview(world),"housing":housing_overview(world),"justice":justice_overview(world),"communications":communication_overview(world),"neighborhoods":neighborhood_overview(world),
        "incidents":[world._incident_summary(incident) for incident in active_incidents],
        "events":[world._event_to_dict(event) for event in world.events[-80:]],
    }
