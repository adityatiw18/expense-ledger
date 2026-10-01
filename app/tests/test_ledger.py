from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app


import pytest
import uuid
from app.models import User
from app.models import Transaction, LedgerEntry
from app.services.balance_service import get_balances
from app.services.ledger_service import (
    create_expense,
    create_settlement,
    correct_expense
)

client = TestClient(app)

def test_get_balances(db, test_data):
    create_expense(
        db=db,
        group_id=test_data["group_id"],
        description="TEST - Balance",
        created_by=test_data["user1"],
        paid_by=test_data["user1"],
        splits={
            test_data["user1"]: Decimal("400"),
            test_data["user2"]: Decimal("300"),
            test_data["user3"]: Decimal("500"),
        }
    )

    balances = get_balances(
        db,
        group_id=test_data["group_id"]
    )

    assert balances[test_data["user1"]] == Decimal("800.00")
    assert balances[test_data["user2"]] == Decimal("-300.00")
    assert balances[test_data["user3"]] == Decimal("-500.00")

def test_create_expense(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]
    user3 = test_data["user3"]

    transaction = create_expense(
        db=db,
        group_id=group_id,
        description="TEST - Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user1: Decimal("400"),
            user2: Decimal("300"),
            user3: Decimal("500"),
        }
    )

    entries = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.transaction_id == transaction.id)
        .all()
    )

    total = sum(entry.amount for entry in entries)

    assert len(entries) == 4
    assert total == Decimal("0.00")


def test_non_member_rejected(db, test_data):
    with pytest.raises(ValueError):
        create_expense(
            db=db,
            group_id=test_data["group_id"],
            description="TEST - Invalid Expense",
            created_by=test_data["user1"],
            paid_by=test_data["user1"],
            splits={
                test_data["user1"]: Decimal("400"),
                999: Decimal("800"),
            }
        )


def test_rollback(db, test_data):
    with pytest.raises(Exception):
        create_expense(
            db=db,
            group_id=test_data["group_id"],
            description="TEST - Rollback",
            created_by=test_data["user1"],
            paid_by=999,
            splits={
                test_data["user1"]: Decimal("600"),
                test_data["user2"]: Decimal("600"),
            }
        )

    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.description == "TEST - Rollback"
        )
        .first()
    )

    assert transaction is None

def test_create_settlement(db, test_data):
    create_expense(
        db=db,
        group_id=test_data["group_id"],
        description="Dinner",
        created_by=test_data["user1"],
        paid_by=test_data["user1"],
        splits={
            test_data["user1"]: Decimal("100.00"),
            test_data["user2"]: Decimal("100.00"),
            test_data["user3"]: Decimal("100.00")
        }
    )

    transaction = create_settlement(
        db=db,
        group_id=test_data["group_id"],
        from_user=test_data["user2"],
        to_user=test_data["user1"],
        amount=Decimal("100.00")
    )

    entries = (
        db.query(LedgerEntry)
        .filter(
            LedgerEntry.transaction_id == transaction.id
        )
        .all()
    )

    assert len(entries) == 2

    balances = {
        entry.user_id: entry.amount
        for entry in entries
    }

    assert balances[test_data["user2"]] == Decimal("100.00")
    assert balances[test_data["user1"]] == Decimal("-100.00")


def test_settlement_exceeds_amount_owed(db, test_data):
    create_expense(
        db=db,
        group_id=test_data["group_id"],
        description="Dinner",
        created_by=test_data["user1"],
        paid_by=test_data["user1"],
        splits={
            test_data["user1"]: Decimal("100.00"),
            test_data["user2"]: Decimal("100.00"),
            test_data["user3"]: Decimal("100.00")
        }
    )

    with pytest.raises(ValueError, match="exceeds amount owed"):
        create_settlement(
            db=db,
            group_id=test_data["group_id"],
            from_user=test_data["user2"],
            to_user=test_data["user1"],
            amount=Decimal("150.00")
        )


def test_settlement_from_user_who_does_not_owe(db, test_data):
    create_expense(
        db=db,
        group_id=test_data["group_id"],
        description="Dinner",
        created_by=test_data["user1"],
        paid_by=test_data["user1"],
        splits={
            test_data["user1"]: Decimal("100.00"),
            test_data["user2"]: Decimal("100.00"),
            test_data["user3"]: Decimal("100.00")
        }
    )

    with pytest.raises(ValueError, match="does not owe money"):
        create_settlement(
            db=db,
            group_id=test_data["group_id"],
            from_user=test_data["user1"],
            to_user=test_data["user2"],
            amount=Decimal("50.00")
        )


def test_settlement_to_user_not_owed(db, test_data):
    create_expense(
        db=db,
        group_id=test_data["group_id"],
        description="Dinner",
        created_by=test_data["user1"],
        paid_by=test_data["user1"],
        splits={
            test_data["user1"]: Decimal("100.00"),
            test_data["user2"]: Decimal("100.00"),
            test_data["user3"]: Decimal("100.00")
        }
    )

    with pytest.raises(ValueError, match="not owed money"):
        create_settlement(
            db=db,
            group_id=test_data["group_id"],
            from_user=test_data["user2"],
            to_user=test_data["user3"],
            amount=Decimal("50.00")
        )

def test_correct_expense(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]
    user3 = test_data["user3"]

    # Original expense:
    # user1 pays 600
    # user2 owes 300
    # user3 owes 300
    original = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user2: Decimal("300"),
            user3: Decimal("300")
        }
    )

    # Correct it:
    # user1 pays 600
    # user2 owes 400
    # user3 owes 200
    corrected = correct_expense(
        db=db,
        transaction_id=original.id,
        created_by=user1,
        description="Corrected Dinner",
        paid_by=user1,
        splits={
            user2: Decimal("400"),
            user3: Decimal("200")
        }
    )

    balances = get_balances(
        db,
        group_id
    )

    assert balances[user1] == Decimal("600")
    assert balances[user2] == Decimal("-400")
    assert balances[user3] == Decimal("-200")

    assert corrected.corrects_transaction_id == original.id

def test_correct_expense_twice(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]
    user3 = test_data["user3"]

    # Original
    original = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user2: Decimal("300"),
            user3: Decimal("300")
        }
    )

    # First correction
    correction1 = correct_expense(
        db=db,
        transaction_id=original.id,
        created_by=user1,
        description="Corrected Dinner 1",
        paid_by=user1,
        splits={
            user2: Decimal("400"),
            user3: Decimal("200")
        }
    )

    # Second correction — correct the first correction
    correction2 = correct_expense(
        db=db,
        transaction_id=correction1.id,
        created_by=user1,
        description="Corrected Dinner 2",
        paid_by=user1,
        splits={
            user2: Decimal("350"),
            user3: Decimal("250")
        }
    )

    balances = get_balances(
        db,
        group_id
    )

    assert balances[user1] == Decimal("600")
    assert balances[user2] == Decimal("-350")
    assert balances[user3] == Decimal("-250")

    assert correction1.corrects_transaction_id == original.id
    assert correction2.corrects_transaction_id == correction1.id

def test_correction_non_member_rejected(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]

    # Create an original expense
    original = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user2: Decimal("100")
        }
    )

    # Create a user who is NOT in the group
    outsider = User(
        name="Outsider",
        email=f"outsider-{uuid.uuid4()}@example.com"
    )

    db.add(outsider)
    db.commit()

    # Try to use outsider as payer
    with pytest.raises(ValueError, match="not a member"):
        correct_expense(
            db=db,
            transaction_id=original.id,
            created_by=user1,
            description="Corrected Dinner",
            paid_by=outsider.id,
            splits={
                user2: Decimal("100")
            }
        )

    db.delete(outsider)
    db.commit()

def test_correction_only_creator_allowed(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]
    user3 = test_data["user3"]

    # user1 creates the expense
    original = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user2: Decimal("300"),
            user3: Decimal("300")
        }
    )

    # user2 tries to correct user1's expense
    with pytest.raises(
        ValueError,
        match="Only the creator can correct this expense"
    ):
        correct_expense(
            db=db,
            transaction_id=original.id,
            created_by=user2,
            description="Unauthorized Correction",
            paid_by=user2,
            splits={
                user2: Decimal("400"),
                user3: Decimal("200")
            }
        )

def test_transaction_types(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]

    # Create an expense
    expense = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user2: Decimal("100")
        }
    )

    assert expense.transaction_type == "EXPENSE"

    # Correct the expense
    corrected = correct_expense(
        db=db,
        transaction_id=expense.id,
        created_by=user1,
        description="Corrected Dinner",
        paid_by=user1,
        splits={
            user2: Decimal("100")
        }
    )

    assert corrected.transaction_type == "EXPENSE"

    # Find the reversal
    reversal = (
        db.query(Transaction)
        .filter(
            Transaction.reverses_transaction_id == expense.id,
            Transaction.transaction_type == "REVERSAL"
        )
        .one()
    )

    assert reversal.transaction_type == "REVERSAL"


def test_correct_expense_api(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]
    user3 = test_data["user3"]

    # Create original expense
    original = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user2: Decimal("300"),
            user3: Decimal("300")
        }
    )

    response = client.put(
        f"/transactions/{original.id}/correct",
        json={
            "description": "Corrected Dinner",
            "created_by": user1,
            "paid_by": user1,
            "splits": {
                str(user2): "400",
                str(user3): "200"
            }
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["description"] == "Corrected Dinner"
    assert "transaction_id" in data
    assert data["transaction_id"] != original.id

def test_correct_nonexistent_transaction_api():
    response = client.put(
        "/transactions/999999999/correct",
        json={
            "description": "Corrected",
            "created_by": 1,
            "paid_by": 1,
            "splits": {
                "2": "100"
            }
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Transaction not found"


def test_unauthorized_correction_api(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]
    user3 = test_data["user3"]

    original = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user2: Decimal("300"),
            user3: Decimal("300")
        }
    )

    response = client.put(
        f"/transactions/{original.id}/correct",
        json={
            "description": "Unauthorized Correction",
            "created_by": user2,
            "paid_by": user2,
            "splits": {
                str(user2): "400",
                str(user3): "200"
            }
        }
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "Only the creator can correct this expense"
    )

def test_non_member_correction_api(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]
    user3 = test_data["user3"]

    original = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user2: Decimal("300"),
            user3: Decimal("300")
        }
    )

    outsider = User(
        name="Outsider",
        email=f"outsider-{uuid.uuid4()}@example.com"
    )

    db.add(outsider)
    db.commit()

    response = client.put(
        f"/transactions/{original.id}/correct",
        json={
            "description": "Invalid Correction",
            "created_by": user1,
            "paid_by": outsider.id,
            "splits": {
                str(user2): "400",
                str(user3): "200"
            }
        }
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        f"User {outsider.id} is not a member of this group"
    )

    db.delete(outsider)
    db.commit()

def test_cannot_correct_settlement(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]
    user3 = test_data["user3"]

    # Create an expense so user2 owes user1
    create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user2: Decimal("100")
        }
    )

    # Create a settlement
    settlement = create_settlement(
        db=db,
        group_id=group_id,
        from_user=user2,
        to_user=user1,
        amount=Decimal("100")
    )

    # Try to correct the settlement
    with pytest.raises(
        ValueError,
        match="Only expense transactions can be corrected"
    ):
        correct_expense(
            db=db,
            transaction_id=settlement.id,
            created_by=user2,
            description="Invalid Correction",
            paid_by=user2,
            splits={
                user1: Decimal("100")
            }
        )

def test_correction_can_change_total(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]
    user3 = test_data["user3"]

    original = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user2: Decimal("300"),
            user3: Decimal("300")
        }
    )

    correct_expense(
        db=db,
        transaction_id=original.id,
        created_by=user1,
        description="Corrected Dinner",
        paid_by=user1,
        splits={
            user2: Decimal("400"),
            user3: Decimal("400")
        }
    )

    balances = get_balances(
        db,
        group_id
    )

    assert balances[user1] == Decimal("800")
    assert balances[user2] == Decimal("-400")
    assert balances[user3] == Decimal("-400")

def test_correction_empty_splits_rejected(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]

    original = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user2: Decimal("100")
        }
    )

    with pytest.raises(
        ValueError,
        match="At least one split is required"
    ):
        correct_expense(
            db=db,
            transaction_id=original.id,
            created_by=user1,
            description="Invalid Correction",
            paid_by=user1,
            splits={}
        )

def test_cannot_correct_reversal(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]

    original = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user2: Decimal("100")
        }
    )

    correct_expense(
        db=db,
        transaction_id=original.id,
        created_by=user1,
        description="Corrected Dinner",
        paid_by=user1,
        splits={
            user2: Decimal("100")
        }
    )

    reversal = (
        db.query(Transaction)
        .filter(
    Transaction.reverses_transaction_id == original.id,
    Transaction.transaction_type == "REVERSAL"
)
        .one()
    )

    with pytest.raises(
        ValueError,
        match="Only expense transactions can be corrected"
    ):
        correct_expense(
            db=db,
            transaction_id=reversal.id,
            created_by=user1,
            description="Invalid Correction",
            paid_by=user1,
            splits={
                user2: Decimal("100")
            }
        )

def test_transaction_ledger_balances_to_zero(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]
    user3 = test_data["user3"]

    transaction = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user1: Decimal("100"),
            user2: Decimal("100"),
            user3: Decimal("100")
        }
    )

    entries = (
        db.query(LedgerEntry)
        .filter(
            LedgerEntry.transaction_id == transaction.id
        )
        .all()
    )

    total = sum(
        entry.amount
        for entry in entries
    )

    assert total == Decimal("0")

def test_non_member_payer_rejected(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]

    non_member = User(
        name="Non Member",
        email=f"non-member-{uuid.uuid4()}@example.com"
    )

    db.add(non_member)
    db.commit()
    db.refresh(non_member)

    with pytest.raises(ValueError, match="not a member"):
        create_expense(
            db=db,
            group_id=group_id,
            description="Dinner",
            created_by=user1,
            paid_by=non_member.id,
            splits={
                user1: Decimal("100"),
                user2: Decimal("100")
            }
        )

def test_group_balances_sum_to_zero(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]
    user3 = test_data["user3"]

    create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user1: Decimal("100"),
            user2: Decimal("100"),
            user3: Decimal("100")
        }
    )

    balances = get_balances(
        db=db,
        group_id=group_id
    )

    total_balance = sum(balances.values())

    assert total_balance == Decimal("0")

def test_reversal_exactly_cancels_original(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]
    user3 = test_data["user3"]

    original = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user1: Decimal("100"),
            user2: Decimal("100"),
            user3: Decimal("100")
        }
    )

    correct_expense(
        db=db,
        transaction_id=original.id,
        created_by=user1,
        description="Corrected Dinner",
        paid_by=user1,
        splits={
            user1: Decimal("100"),
            user2: Decimal("100"),
            user3: Decimal("100")
        }
    )

    original_entries = (
        db.query(LedgerEntry)
        .filter(
            LedgerEntry.transaction_id == original.id
        )
        .all()
    )

    reversal = (
        db.query(Transaction)
        .filter(
            Transaction.reverses_transaction_id == original.id,
            Transaction.transaction_type == "REVERSAL"
        )
        .one()
    )

    reversal_entries = (
        db.query(LedgerEntry)
        .filter(
            LedgerEntry.transaction_id == reversal.id
        )
        .all()
    )

    original_by_user = {
        entry.user_id: entry.amount
        for entry in original_entries
    }

    reversal_by_user = {
        entry.user_id: entry.amount
        for entry in reversal_entries
    }

    assert set(original_by_user.keys()) == set(reversal_by_user.keys())

    for user_id in original_by_user:
        assert reversal_by_user[user_id] == -original_by_user[user_id]

def test_invalid_split_amount_rejected(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]

    with pytest.raises(ValueError, match="Split amounts must be positive"):
        create_expense(
            db=db,
            group_id=group_id,
            description="Invalid Dinner",
            created_by=user1,
            paid_by=user1,
            splits={
                user1: Decimal("100"),
                user2: Decimal("-50")
            }
        )

def test_empty_split_rejected(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]

    with pytest.raises(ValueError, match="At least one split"):
        create_expense(
            db=db,
            group_id=group_id,
            description="Invalid Expense",
            created_by=user1,
            paid_by=user1,
            splits={}
        )

def test_only_creator_can_correct_expense(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]

    transaction = create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user1,
        paid_by=user1,
        splits={
            user1: Decimal("100"),
            user2: Decimal("100")
        }
    )

    with pytest.raises(
        ValueError,
        match="Only the creator can correct this expense"
    ):
        correct_expense(
            db=db,
            transaction_id=transaction.id,
            created_by=user2,
            description="Unauthorized Correction",
            paid_by=user2,
            splits={
                user1: Decimal("50"),
                user2: Decimal("50")
            }
        )

def test_correct_nonexistent_transaction_rejected(db, test_data):
    user1 = test_data["user1"]
    user2 = test_data["user2"]

    with pytest.raises(ValueError, match="Transaction not found"):
        correct_expense(
            db=db,
            transaction_id=999999,
            created_by=user1,
            description="Invalid Correction",
            paid_by=user1,
            splits={
                user1: Decimal("50"),
                user2: Decimal("50")
            }
        )

def test_cannot_correct_settlement(db, test_data):
    group_id = test_data["group_id"]
    user1 = test_data["user1"]
    user2 = test_data["user2"]

    create_expense(
        db=db,
        group_id=group_id,
        description="Dinner",
        created_by=user2,
        paid_by=user2,
        splits={
            user1: Decimal("50"),
            user2: Decimal("50")
        }
    )

    settlement = create_settlement(
        db=db,
        group_id=group_id,
        from_user=user1,
        to_user=user2,
        amount=Decimal("50")
    )

    with pytest.raises(
        ValueError,
        match="Only expense transactions can be corrected"
    ):
        correct_expense(
            db=db,
            transaction_id=settlement.id,
            created_by=user1,
            description="Invalid Correction",
            paid_by=user1,
            splits={
                user1: Decimal("25"),
                user2: Decimal("25")
            }
        )

