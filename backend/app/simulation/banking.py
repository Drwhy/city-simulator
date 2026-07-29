from __future__ import annotations

import random
from typing import TYPE_CHECKING

from .models import BankTransaction, BuildingType, Citizen

if TYPE_CHECKING:
    from .world import World


MAX_BANKING_HISTORY = 60


def bank(world: World):
    return next(
        (building for building in world.buildings.values() if building.building_type == BuildingType.BANK),
        None,
    )


def initialize_banking(world: World) -> None:
    world.banking_rng = random.Random(world.seed + 50_021)
    world._last_banking_day = 0
    world.bank_loans_issued_today = 0.0
    world.bank_defaults_today = 0.0
    institution = bank(world)
    if institution is not None and institution.bank_reserves <= 0:
        institution.bank_reserves = 120_000.0
    for citizen in world.citizens.values():
        if citizen.bank_balance == 0 and citizen.savings_balance == 0 and citizen.bank_debt == 0:
            deposited = round(max(0.0, citizen.money) * 0.55, 2)
            citizen.money = round(citizen.money - deposited, 2)
            citizen.bank_balance = deposited
        citizen.credit_score = max(0.0, min(100.0, citizen.credit_score))


def available_funds(citizen: Citizen, *, allow_credit: bool = False) -> float:
    amount = max(0.0, citizen.money) + max(0.0, citizen.bank_balance)
    if allow_credit:
        amount += max(0.0, citizen.overdraft_limit + min(0.0, citizen.money))
    return round(amount, 2)


def _record(
    citizen: Citizen,
    *,
    tick: int,
    transaction_type: str,
    amount: float,
    label: str,
    counterparty_id: int | None = None,
) -> None:
    citizen.banking_history.append(
        BankTransaction(
            tick=tick,
            transaction_type=transaction_type,
            amount=round(amount, 2),
            balance_after=round(citizen.bank_balance, 2),
            label=label,
            counterparty_id=counterparty_id,
        )
    )
    citizen.banking_history[:] = citizen.banking_history[-MAX_BANKING_HISTORY:]


def deposit(
    world: World,
    citizen: Citizen,
    amount: float,
    *,
    label: str,
    transaction_type: str = "deposit",
    counterparty_id: int | None = None,
    cash_share: float = 0.0,
) -> float:
    amount = round(max(0.0, amount), 2)
    cash_amount = round(amount * max(0.0, min(1.0, cash_share)), 2)
    account_amount = round(amount - cash_amount, 2)
    citizen.money = round(citizen.money + cash_amount, 2)
    citizen.bank_balance = round(citizen.bank_balance + account_amount, 2)
    _record(
        citizen,
        tick=world.tick,
        transaction_type=transaction_type,
        amount=account_amount,
        label=label,
        counterparty_id=counterparty_id,
    )
    return amount


def withdraw(
    world: World,
    citizen: Citizen,
    amount: float,
    *,
    label: str,
    transaction_type: str = "payment",
    counterparty_id: int | None = None,
    allow_credit: bool = False,
) -> float:
    requested = round(max(0.0, amount), 2)
    remaining = requested
    cash_paid = min(max(0.0, citizen.money), remaining)
    citizen.money = round(citizen.money - cash_paid, 2)
    remaining = round(remaining - cash_paid, 2)
    account_paid = min(max(0.0, citizen.bank_balance), remaining)
    citizen.bank_balance = round(citizen.bank_balance - account_paid, 2)
    remaining = round(remaining - account_paid, 2)
    credit_paid = 0.0
    if allow_credit and remaining > 0:
        credit_available = max(0.0, citizen.overdraft_limit + min(0.0, citizen.money))
        credit_paid = min(credit_available, remaining)
        citizen.money = round(citizen.money - credit_paid, 2)
        remaining = round(remaining - credit_paid, 2)
    paid = round(requested - remaining, 2)
    if paid:
        _record(
            citizen,
            tick=world.tick,
            transaction_type=transaction_type,
            amount=-paid,
            label=label,
            counterparty_id=counterparty_id,
        )
    return paid


def request_loan(world: World, citizen: Citizen, amount: float, *, reason: str) -> float:
    institution = bank(world)
    requested = round(max(0.0, amount), 2)
    if (
        institution is None
        or requested <= 0
        or citizen.credit_score < 38
        or citizen.bank_debt > max(250.0, citizen.salary_daily * 25)
        or institution.bank_reserves < requested
    ):
        citizen.credit_score = max(0.0, citizen.credit_score - 1.5)
        return 0.0
    institution.bank_reserves = round(institution.bank_reserves - requested, 2)
    institution.outstanding_loans = round(institution.outstanding_loans + requested, 2)
    citizen.bank_debt = round(citizen.bank_debt + requested, 2)
    citizen.bank_balance = round(citizen.bank_balance + requested, 2)
    citizen.credit_score = max(0.0, citizen.credit_score - requested / 500.0)
    world.bank_loans_issued_today = round(world.bank_loans_issued_today + requested, 2)
    _record(
        citizen,
        tick=world.tick,
        transaction_type="loan",
        amount=requested,
        label=f"Crédit bancaire : {reason}",
        counterparty_id=institution.id,
    )
    world._emit(
        "bank_loan_issued",
        f"{citizen.full_name} obtient un crédit de {requested:.2f} € ({reason}).",
        citizen_ids=(citizen.id,),
        building_id=institution.id,
    )
    return requested


def update_banking(world: World) -> None:
    if world.hour != 0 or world.minute != 7 or world._last_banking_day == world.day:
        return
    world._last_banking_day = world.day
    institution = bank(world)
    if institution is None:
        return
    for citizen in world.citizens.values():
        if citizen.bank_debt > 0:
            interest = round(citizen.bank_debt * 0.00045, 2)
            citizen.bank_debt = round(citizen.bank_debt + interest, 2)
            institution.outstanding_loans = round(institution.outstanding_loans + interest, 2)
            institution.interest_income = round(institution.interest_income + interest, 2)
            due = round(min(citizen.bank_debt, max(2.0, citizen.salary_daily * 0.035)), 2)
            paid = withdraw(world, citizen, due, label="Échéance de crédit", transaction_type="loan_payment")
            citizen.bank_debt = round(citizen.bank_debt - paid, 2)
            institution.outstanding_loans = round(max(0.0, institution.outstanding_loans - paid), 2)
            institution.bank_reserves = round(institution.bank_reserves + paid, 2)
            if paid + 0.01 < due:
                citizen.credit_score = max(0.0, citizen.credit_score - 2.0)
                world.bank_defaults_today = round(world.bank_defaults_today + due - paid, 2)
            else:
                citizen.credit_score = min(100.0, citizen.credit_score + 0.15)
        if citizen.bank_balance > max(600.0, citizen.salary_daily * 8) and world.banking_rng.random() < 0.08:
            saved = round(citizen.bank_balance * 0.05, 2)
            citizen.bank_balance = round(citizen.bank_balance - saved, 2)
            citizen.savings_balance = round(citizen.savings_balance + saved, 2)
            _record(citizen, tick=world.tick, transaction_type="savings", amount=-saved, label="Versement épargne")


def banking_overview(world: World) -> dict[str, object]:
    institution = bank(world)
    citizens = list(world.citizens.values())
    return {
        "tick": world.tick,
        "bank": {
            "id": institution.id if institution else None,
            "name": institution.name if institution else None,
            "reserves": round(institution.bank_reserves, 2) if institution else 0.0,
            "outstandingLoans": round(institution.outstanding_loans, 2) if institution else 0.0,
            "interestIncome": round(institution.interest_income, 2) if institution else 0.0,
        },
        "metrics": {
            "deposits": round(sum(row.bank_balance for row in citizens), 2),
            "savings": round(sum(row.savings_balance for row in citizens), 2),
            "citizenDebt": round(sum(row.bank_debt for row in citizens), 2),
            "borrowers": sum(row.bank_debt > 0 for row in citizens),
            "loansIssuedToday": round(world.bank_loans_issued_today, 2),
            "defaultsToday": round(world.bank_defaults_today, 2),
        },
    }
