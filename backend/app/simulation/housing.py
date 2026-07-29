from __future__ import annotations

from statistics import median
from typing import TYPE_CHECKING

from .models import Building, BuildingType, Household, HousingRecord, TravelStage

if TYPE_CHECKING:
    from .world import World

SEARCH_COOLDOWN = 7 * 24 * 60
MAX_HISTORY = 30


def initialize_housing(world: World) -> None:
    homes = sorted((b for b in world.buildings.values() if b.building_type == BuildingType.HOME), key=lambda b: b.id)
    for index, home in enumerate(homes):
        if home.rent_monthly <= 0:
            location = abs(home.x - 20) + abs(home.y - 11)
            home.comfort = round(45.0 + (index * 13 % 43), 1)
            home.housing_condition = round(55.0 + (index * 17 % 40), 1)
            home.rent_monthly = round(300.0 + home.capacity * 34.0 + home.comfort * 2.2 - min(90.0, location * 3.0), 2)
            home.owner_type = "municipal" if index % 6 == 0 else "private"
    world._last_housing_day = getattr(world, "_last_housing_day", 0)
    world.moves_today = getattr(world, "moves_today", 0)


def residents(world: World, home_id: int) -> list[int]:
    return sorted(c.id for c in world.citizens.values() if c.home_id == home_id)


def household_income_monthly(world: World, household: Household) -> float:
    return round(sum(max(0.0, world.citizens[cid].salary_daily) * len(world.citizens[cid].work_days) * 4.33 for cid in household.member_ids), 2)


def common_budget(world: World, household: Household) -> float:
    return round(sum(world.citizens[cid].money + world.citizens[cid].bank_balance + world.citizens[cid].savings_balance - world.citizens[cid].bank_debt for cid in household.member_ids), 2)


def commute_distance(world: World, household: Household, home_id: int | None = None) -> float:
    home = world.buildings[home_id if home_id is not None else household.home_id]
    distances = [abs(home.entrance[0] - world.buildings[c.workplace_id].entrance[0]) + abs(home.entrance[1] - world.buildings[c.workplace_id].entrance[1]) for cid in household.member_ids if (c := world.citizens[cid]).workplace_id in world.buildings]
    return round(sum(distances) / max(1, len(distances)), 1)


def service_distance(world: World, home: Building) -> float:
    services = [b for b in world.buildings.values() if b.building_type in {BuildingType.SHOP, BuildingType.PUBLIC, BuildingType.HOSPITAL, BuildingType.PARK}]
    return float(min((abs(home.entrance[0]-b.entrance[0])+abs(home.entrance[1]-b.entrance[1]) for b in services), default=0))


def neighborhood_safety(world: World, home: Building) -> float:
    recent = sum(1 for incident in world.incidents.values() if world.tick - incident.created_tick <= 7*24*60 and abs(home.entrance[0]-incident.x)+abs(home.entrance[1]-incident.y) <= 7)
    return round(max(0.0, 100.0 - recent * 12.0), 1)


def housing_reason(world: World, household: Household) -> str | None:
    if household.housing_status == "homeless":
        return "sans logement"
    home = world.buildings[household.home_id]
    count = len(household.member_ids)
    income = household_income_monthly(world, household)
    if count > home.capacity:
        return "surpeuplement"
    if household.missed_rent_days >= 2 or (income > 0 and home.rent_monthly / income > 0.38):
        return "loyer trop élevé"
    if commute_distance(world, household) > 28 and world.tick - household.last_move_tick >= SEARCH_COOLDOWN:
        return "trajet domicile-travail trop long"
    if home.housing_condition < 35:
        return "logement dégradé"
    return None


def update_housing(world: World) -> None:
    if world.hour != 6 or world.minute != 10 or world._last_housing_day == world.day:
        return
    world._last_housing_day = world.day
    for household in sorted(list(world.households.values()), key=lambda h: h.id):
        if household.id not in world.households:
            continue
        members = [world.citizens[cid] for cid in household.member_ids]
        for citizen in members:
            if citizen.food_units < 0.25 and citizen.money + citizen.bank_balance <= 0:
                citizen.food_insecurity_days += 1
            else:
                citizen.food_insecurity_days = max(0, citizen.food_insecurity_days - 1)
        if household.housing_status == "homeless":
            destination = best_home(world, household, "sans logement")
            if destination is not None and common_budget(world, household) >= destination.rent_monthly * 0.5:
                move_household(world, household, destination.id, "retour vers un logement stable")
                for citizen in members:
                    citizen.is_homeless = False
                    citizen.homeless_since_tick = None
            continue
        if any(citizen.food_insecurity_days >= 3 for citizen in members):
            become_homeless(world, household, "absence durable de ressources pour se nourrir")
            continue
        if household.cohesion < 12 and household.conflicts >= 5 and len(household.member_ids) >= 2 and world.tick - household.last_move_tick >= SEARCH_COOLDOWN:
            split_household(world, household)
        reason = housing_reason(world, household)
        if reason is None:
            if household.housing_status == "searching":
                household.housing_status = "stable"
                household.housing_search_since_tick = None
                household.housing_search_reason = None
            continue
        if household.housing_status != "searching":
            household.housing_status = "searching"
            household.housing_search_since_tick = world.tick
            household.housing_search_reason = reason
            world._emit("housing_search_started", f"Le foyer #{household.id} cherche un logement : {reason}.", citizen_ids=tuple(household.member_ids), building_id=household.home_id, severity="warning")
        if world.tick - household.last_move_tick < SEARCH_COOLDOWN:
            continue
        destination = best_home(world, household, reason)
        if destination is not None:
            move_household(world, household, destination.id, reason)
        elif household.missed_rent_days >= 4:
            place_temporary(world, household)
        if household.missed_rent_days >= 7 or any(citizen.food_insecurity_days >= 3 for citizen in members):
            become_homeless(world, household, "impayés de loyer" if household.missed_rent_days >= 7 else "absence durable de ressources pour se nourrir")


def best_home(world: World, household: Household, reason: str) -> Building | None:
    count = len(household.member_ids)
    current = world.buildings[household.home_id]
    income = household_income_monthly(world, household)
    occupied = {h.home_id for h in world.households.values() if h.id != household.id and h.temporary_host_household_id is None}
    candidates = [h for h in world.buildings.values() if h.building_type == BuildingType.HOME and h.id != current.id and h.id not in occupied and h.capacity >= count]
    if not candidates:
        return None
    def score(home: Building) -> float:
        affordability = max(0.0, 1.0 - home.rent_monthly / max(1.0, income * 0.36)) * 42.0
        size_fit = max(0.0, 18.0 - abs(home.capacity-count)*3.0)
        return affordability + size_fit + home.comfort*.16 + home.housing_condition*.10 + neighborhood_safety(world, home)*.08 - commute_distance(world, household, home.id)*.7 - service_distance(world, home)*.25
    if reason == "loyer trop élevé":
        affordable = [home for home in candidates if home.rent_monthly <= current.rent_monthly * 0.9]
        return max(affordable, key=lambda h: (score(h), -h.id), default=None)
    destination = max(candidates, key=lambda h: (score(h), -h.id))
    if reason == "surpeuplement":
        return destination
    if score(destination) - score(current) < 8.0:
        return None
    return destination


def move_household(world: World, household: Household, destination_id: int, reason: str, *, event_type: str = "move") -> None:
    origin = world.buildings[household.home_id]
    destination = world.buildings[destination_id]
    member_ids = list(household.member_ids)
    label = "Séparation et nouveau foyer" if event_type == "separation" else "Hébergement temporaire" if event_type == "temporary" else "Déménagement"
    record = HousingRecord(world.tick, event_type, label, origin.id, destination.id, reason, origin.rent_monthly, destination.rent_monthly, member_ids)
    for cid in member_ids:
        citizen = world.citizens[cid]
        citizen.home_id = destination.id
        if citizen.travel_stage == TravelStage.IDLE and (citizen.x, citizen.y) == origin.entrance:
            origin.occupants.discard(cid)
            destination.occupants.add(cid)
            citizen.x, citizen.y = destination.entrance
        if citizen.owned_vehicle_id in world.vehicles:
            vehicle = world.vehicles[citizen.owned_vehicle_id]
            if vehicle.current_building_id == origin.id:
                vehicle.current_building_id = destination.id
                vehicle.x, vehicle.y = destination.entrance
    household.home_id = destination.id
    household.moves += 1
    household.last_move_tick = world.tick
    household.housing_status = "temporary" if event_type == "temporary" else "stable"
    household.housing_search_since_tick = None
    household.housing_search_reason = None
    household.housing_history.append(record)
    household.housing_history[:] = household.housing_history[-MAX_HISTORY:]
    origin.housing_history.append(record)
    destination.housing_history.append(record)
    origin.housing_history[:] = origin.housing_history[-MAX_HISTORY:]
    destination.housing_history[:] = destination.housing_history[-MAX_HISTORY:]
    world.moves_today += 1
    world._emit("household_moved" if event_type == "move" else "temporary_housing", f"Le foyer #{household.id} quitte {origin.name} pour {destination.name} ({reason}).", citizen_ids=tuple(member_ids), building_id=destination.id, severity="warning" if event_type == "temporary" else "info")


def split_household(world: World, household: Household) -> Household | None:
    """Séparation explicite et rare : un membre adulte forme un nouveau foyer relogé."""
    if len(household.member_ids) < 2:
        return None
    member_id = max(household.member_ids, key=lambda cid: (world.citizens[cid].age, cid))
    occupied = {row.home_id for row in world.households.values() if row.temporary_host_household_id is None}
    homes = [home for home in world.buildings.values() if home.building_type == BuildingType.HOME and home.id not in occupied and home.capacity >= 1]
    if not homes:
        return None
    citizen = world.citizens[member_id]
    destination = min(homes, key=lambda home: (home.rent_monthly + (abs(home.entrance[0]-world.buildings[citizen.workplace_id].entrance[0])+abs(home.entrance[1]-world.buildings[citizen.workplace_id].entrance[1]) if citizen.workplace_id in world.buildings else 0)*8, home.id))
    household.member_ids.remove(member_id)
    new_household = Household(id=max(world.households, default=0)+1, home_id=household.home_id, member_ids=[member_id], cohesion=50.0, last_move_tick=-SEARCH_COOLDOWN)
    world.households[new_household.id] = new_household
    citizen.household_id = new_household.id
    move_household(world, new_household, destination.id, "séparation explicite du foyer", event_type="separation")
    household.housing_history.append(HousingRecord(world.tick, "separation", "Séparation du foyer", household.home_id, household.home_id, f"{citizen.full_name} forme un nouveau foyer", world.buildings[household.home_id].rent_monthly, world.buildings[household.home_id].rent_monthly, [member_id]))
    world._emit("household_separated", f"{citizen.full_name} quitte explicitement le foyer #{household.id} et forme le foyer #{new_household.id}.", citizen_ids=(member_id,), building_id=destination.id, severity="warning")
    return new_household


def place_temporary(world: World, household: Household) -> None:
    count = len(household.member_ids)
    hosts = []
    for other in world.households.values():
        if other.id == household.id:
            continue
        capacity = world.buildings[other.home_id].capacity
        if len(residents(world, other.home_id)) + count > capacity + 2:
            continue
        relationship = max((world.citizens[cid].relationships.get(oid) for cid in household.member_ids for oid in other.member_ids), key=lambda r: r.trust if r else -100, default=None)
        if relationship and relationship.trust >= 35:
            hosts.append((relationship.trust, other))
    if hosts:
        host = max(hosts, key=lambda row: (row[0], -row[1].id))[1]
        household.temporary_host_household_id = host.id
        move_household(world, household, host.home_id, "hébergement temporaire chez un proche", event_type="temporary")
        return
    municipal = min((h for h in world.buildings.values() if h.building_type == BuildingType.HOME and h.owner_type == "municipal"), key=lambda h: (len(residents(world,h.id))/max(1,h.capacity), h.rent_monthly), default=None)
    if municipal is not None:
        household.temporary_host_household_id = None
        move_household(world, household, municipal.id, "relogement municipal temporaire", event_type="temporary")
        return
    become_homeless(world, household, "aucune solution d'hébergement disponible")


def become_homeless(world: World, household: Household, reason: str) -> None:
    if household.housing_status == "homeless":
        return
    origin = world.buildings[household.home_id]
    shelter = next((building for building in world.buildings.values() if building.building_type == BuildingType.SHELTER and len(residents(world, building.id)) + len(household.member_ids) <= building.capacity), None)
    destination = shelter or next(building for building in world.buildings.values() if building.building_type == BuildingType.PARK)
    household.home_id = destination.id
    household.housing_status = "homeless"
    household.housing_search_since_tick = world.tick
    household.housing_search_reason = reason
    household.temporary_host_household_id = None
    household.last_move_tick = world.tick
    for citizen_id in household.member_ids:
        citizen = world.citizens[citizen_id]
        citizen.previous_home_id = origin.id
        citizen.home_id = destination.id
        citizen.is_homeless = True
        citizen.homeless_since_tick = world.tick
        if citizen.travel_stage == TravelStage.IDLE:
            origin.occupants.discard(citizen_id)
            destination.occupants.add(citizen_id)
            citizen.x, citizen.y = destination.entrance
        citizen.needs.stress = min(100.0, citizen.needs.stress + 18.0)
    world._emit("household_became_homeless", f"Le foyer #{household.id} devient sans abri : {reason}.", citizen_ids=tuple(household.member_ids), building_id=destination.id, severity="critical")


def charge_daily_rent(world: World, household: Household) -> float:
    from .banking import available_funds, withdraw
    if household.housing_status == "homeless":
        household.rent_due_today = 0.0
        household.rent_paid_today = 0.0
        return 0.0
    due = round(world.buildings[household.home_id].rent_monthly / 30.0, 2)
    household.rent_due_today = due
    remaining = due
    members = [world.citizens[cid] for cid in household.member_ids]
    for citizen in sorted(members, key=lambda item: available_funds(item, allow_credit=True), reverse=True):
        paid = withdraw(world, citizen, remaining, label=f"Loyer — {world.buildings[household.home_id].name}", transaction_type="rent", counterparty_id=household.home_id, allow_credit=True)
        citizen.expenses_today = round(citizen.expenses_today+paid, 2)
        remaining = round(remaining-paid, 2)
        if remaining <= 0:
            break
    paid = round(due-remaining, 2)
    household.rent_paid_today = paid
    if remaining > 0:
        household.rent_arrears = round(household.rent_arrears+remaining, 2)
        household.missed_rent_days += 1
    elif household.rent_arrears > 0:
        repayment = min(household.rent_arrears, max(0.0, common_budget(world, household)*.05))
        household.rent_arrears = round(household.rent_arrears-repayment, 2)
        household.missed_rent_days = max(0, household.missed_rent_days-1)
    return paid


def housing_metrics(world: World) -> dict[str, float | int]:
    homes = [h for h in world.buildings.values() if h.building_type == BuildingType.HOME]
    occupied = {h.home_id for h in world.households.values()}
    commute = [commute_distance(world,h) for h in world.households.values()]
    return {"medianRent": round(median([h.rent_monthly for h in homes]),2) if homes else 0.0, "vacancyRate": round((len(homes)-len(occupied))/max(1,len(homes))*100,1), "overcrowdedHouseholds": sum(len(h.member_ids)>world.buildings[h.home_id].capacity for h in world.households.values()), "distressedHouseholds": sum(h.rent_arrears>0 or h.housing_status in {"searching","temporary"} for h in world.households.values()), "movesToday": world.moves_today, "averageHomeWorkDistance": round(sum(commute)/max(1,len(commute)),1), "searchingHouseholds": sum(h.housing_status=="searching" for h in world.households.values()), "temporaryHouseholds": sum(h.housing_status=="temporary" for h in world.households.values()), "homelessCitizens": sum(c.is_homeless for c in world.citizens.values()), "homelessHouseholds": sum(h.housing_status=="homeless" for h in world.households.values())}


def housing_overview(world: World) -> dict[str, object]:
    return {"tick": world.tick, "metrics": housing_metrics(world), "homes": [home_summary(world,h) for h in world.buildings.values() if h.building_type == BuildingType.HOME], "households": [household_summary(world,h) for h in world.households.values()]}


def home_summary(world: World, home: Building) -> dict[str, object]:
    resident_ids = residents(world, home.id)
    return {"id":home.id,"name":home.name,"capacity":home.capacity,"residentCount":len(resident_ids),"availablePlaces":max(0,home.capacity-len(resident_ids)),"rentMonthly":round(home.rent_monthly,2),"condition":round(home.housing_condition,1),"comfort":round(home.comfort,1),"ownerType":home.owner_type,"serviceDistance":service_distance(world,home),"safety":neighborhood_safety(world,home),"available":not any(h.home_id==home.id and h.temporary_host_household_id is None for h in world.households.values())}


def household_summary(world: World, household: Household) -> dict[str, object]:
    home=world.buildings[household.home_id]
    return {"id":household.id,"homeId":home.id,"homeName":home.name,"members":len(household.member_ids),"status":household.housing_status,"rentMonthly":round(home.rent_monthly,2),"rentArrears":round(household.rent_arrears,2),"incomeMonthly":household_income_monthly(world,household),"commonBudget":common_budget(world,household),"overcrowded":len(household.member_ids)>home.capacity,"commuteDistance":commute_distance(world,household),"moves":household.moves,"searchReason":household.housing_search_reason}
