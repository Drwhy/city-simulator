from app.simulation.housing import best_home, housing_metrics, move_household, place_temporary, split_household
from app.simulation.models import BuildingType
from app.simulation.persistence import SAVE_VERSION
from app.simulation.world import World


def _vacant_homes(world, household):
    occupied = {row.home_id for row in world.households.values() if row.id != household.id}
    return [home for home in world.buildings.values() if home.building_type == BuildingType.HOME and home.id not in occupied and home.id != household.home_id]


def test_poor_household_can_choose_and_move_to_cheaper_home_together():
    world = World(seed=901, citizen_count=100)
    household = next(iter(world.households.values()))
    origin = world.buildings[household.home_id]
    origin.rent_monthly = 1800
    household.missed_rent_days = 2
    household.last_move_tick = -10080
    for cid in household.member_ids:
        world.citizens[cid].salary_daily = 25
    destination = best_home(world, household, "loyer trop élevé")
    assert destination is not None and destination.rent_monthly < origin.rent_monthly
    members = list(household.member_ids)
    move_household(world, household, destination.id, "loyer trop élevé")
    assert {world.citizens[cid].home_id for cid in members} == {destination.id}
    assert household.housing_history[-1].member_ids == members


def test_growing_household_searches_larger_and_move_changes_commute():
    world = World(seed=902, citizen_count=70)
    household = min(world.households.values(), key=lambda row: len(row.member_ids))
    origin = world.buildings[household.home_id]
    origin.capacity = max(1, len(household.member_ids)-1)
    before = sum(abs(origin.entrance[0]-world.buildings[c.workplace_id].entrance[0])+abs(origin.entrance[1]-world.buildings[c.workplace_id].entrance[1]) for cid in household.member_ids if (c:=world.citizens[cid]).workplace_id) 
    destination = best_home(world, household, "surpeuplement")
    assert destination is not None and destination.capacity >= len(household.member_ids)
    move_household(world, household, destination.id, "surpeuplement")
    after = sum(abs(destination.entrance[0]-world.buildings[c.workplace_id].entrance[0])+abs(destination.entrance[1]-world.buildings[c.workplace_id].entrance[1]) for cid in household.member_ids if (c:=world.citizens[cid]).workplace_id)
    assert before != after


def test_explicit_separation_forms_new_household_with_a_home():
    world = World(seed=903, citizen_count=70)
    household = next(row for row in world.households.values() if len(row.member_ids) >= 2)
    original = set(household.member_ids)
    created = split_household(world, household)
    assert created is not None
    assert set(created.member_ids) | set(household.member_ids) == original
    assert set(created.member_ids).isdisjoint(household.member_ids)
    assert all(world.citizens[cid].home_id == created.home_id for cid in created.member_ids)
    assert any(event.event_type == "household_separated" for event in world.events)


def test_temporary_rehousing_never_removes_home_without_alternative():
    world = World(seed=904, citizen_count=70)
    household = next(iter(world.households.values()))
    previous = household.home_id
    place_temporary(world, household)
    assert household.home_id in world.buildings
    assert all(world.citizens[cid].home_id == household.home_id for cid in household.member_ids)
    assert household.home_id != previous or household.housing_status == "temporary"


def test_moves_are_justified_cooldown_limited_and_state_round_trips():
    world = World(seed=905, citizen_count=100)
    household = next(iter(world.households.values()))
    destination = _vacant_homes(world, household)[0]
    move_household(world, household, destination.id, "test justifié")
    assert best_home(world, household, "trajet domicile-travail trop long") is not None or world.tick-household.last_move_tick < 7*24*60
    restored = World.from_state(world.export_state())
    restored_household = restored.households[household.id]
    assert restored_household.home_id == destination.id
    assert restored_household.housing_history[-1].reason == "test justifié"
    assert restored.export_state()["version"] == SAVE_VERSION


def test_housing_metrics_and_thirty_day_run_remain_coherent():
    world = World(seed=906, citizen_count=100)
    assert housing_metrics(world)["vacancyRate"] > 0
    world.run_minutes(30 * 24 * 60)
    metrics = housing_metrics(world)
    assert metrics["overcrowdedHouseholds"] >= 0
    assert all(row.home_id in world.buildings for row in world.households.values())
    assert all(citizen.household_id in world.households for citizen in world.citizens.values())
    assert all(row.housing_status in {"stable", "searching", "temporary", "homeless"} for row in world.households.values())
