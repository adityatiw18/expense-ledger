from decimal import Decimal

from app.services.ledger_service import create_expense
from app.services.settlement_service import (
    calculate_settlements,
    get_group_settlements
)


def apply_settlements(balances, settlements):
    result = balances.copy()

    for payer, receiver, amount in settlements:
        result[payer] += amount
        result[receiver] -= amount

    return result


def test_simple_settlement():
    balances = {
        1: Decimal("800"),
        2: Decimal("-300"),
        3: Decimal("-500"),
    }

    result = calculate_settlements(balances)

    final_balances = apply_settlements(
        balances,
        result
    )

    assert all(
        balance == Decimal("0")
        for balance in final_balances.values()
    )

    assert len(result) == 2


def test_partial_matching():
    balances = {
        1: Decimal("500"),
        2: Decimal("300"),
        3: Decimal("-400"),
        4: Decimal("-400"),
    }

    result = calculate_settlements(balances)

    final_balances = apply_settlements(
        balances,
        result
    )

    assert all(
        balance == Decimal("0")
        for balance in final_balances.values()
    )

    assert len(result) == 3


def test_already_settled():
    balances = {
        1: Decimal("0"),
        2: Decimal("0"),
    }

    result = calculate_settlements(balances)

    assert result == []


def test_group_settlement(db, test_data):

    create_expense(
        db=db,
        group_id=test_data["group_id"],
        description="TEST - Settlement",
        created_by=test_data["user1"],
        paid_by=test_data["user1"],
        splits={
            test_data["user1"]: Decimal("400"),
            test_data["user2"]: Decimal("300"),
            test_data["user3"]: Decimal("500"),
        }
    )

    result = get_group_settlements(
        db,
        test_data["group_id"]
    )

    assert len(result) == 2