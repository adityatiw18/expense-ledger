from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Group,
    Transaction,
    LedgerEntry,
    GroupMember
)

from .balance_service import get_balances


def create_expense(
    db: Session,
    group_id: int,
    description: str,
    created_by: int,
    paid_by: int,
    splits: dict[int, Decimal],
):
    if not splits:
        raise ValueError("At least one split is required")

    if any(amount <= 0 for amount in splits.values()):
        raise ValueError("Split amounts must be positive")

    total = sum(splits.values())

    if total <= 0:
        raise ValueError("Expense total must be positive")

    try:
        db.execute(
            select(Group)
            .where(Group.id == group_id)
            .with_for_update()
        )

        members = {
            member.user_id
            for member in db.query(GroupMember)
            .filter(GroupMember.group_id == group_id)
            .all()
        }
        if paid_by not in members:
            raise ValueError(
                f"User {paid_by} is not a member of this group"
        )

        for user_id in splits:
            if user_id not in members:
                raise ValueError(
                    f"User {user_id} is not a member of this group"
                )

        transaction = Transaction(
    group_id=group_id,
    description=description,
    created_by=created_by,
    transaction_type="EXPENSE"
)

        db.add(transaction)
        db.flush()

        db.add(
            LedgerEntry(
                transaction_id=transaction.id,
                user_id=paid_by,
                amount=total
            )
        )

        for user_id, amount in splits.items():
            db.add(
                LedgerEntry(
                    transaction_id=transaction.id,
                    user_id=user_id,
                    amount=-amount
                )
            )

        db.commit()

        return transaction

    except Exception:
        db.rollback()
        raise


def correct_expense(
    db: Session,
    transaction_id: int,
    created_by: int,
    description: str,
    splits: dict[int, Decimal],
    paid_by: int,
):
    if not splits:
        raise ValueError("At least one split is required")

    if any(amount <= 0 for amount in splits.values()):
        raise ValueError("Split amounts must be positive")

    total = sum(splits.values())

    if total <= 0:
        raise ValueError("Expense total must be positive")

    try:
        # Lock the original transaction
        original = (
            db.execute(
                select(Transaction)
                .where(Transaction.id == transaction_id)
                .with_for_update()
            )
            .scalar_one_or_none()
        )

        if original is None:
            raise ValueError("Transaction not found")

        if original.created_by != created_by:
            raise ValueError(
        "Only the creator can correct this expense"
    )
        if original.transaction_type != "EXPENSE":
            raise ValueError(
        "Only expense transactions can be corrected"
    )

        # Lock the group so the correction is concurrency-safe
        db.execute(
            select(Group)
            .where(Group.id == original.group_id)
            .with_for_update()
        )

        # Get group members
        members = {
            member.user_id
            for member in db.query(GroupMember)
            .filter(
                GroupMember.group_id == original.group_id
            )
            .all()
        }

        if paid_by not in members:
            raise ValueError(
                f"User {paid_by} is not a member of this group"
            )

        for user_id in splits:
            if user_id not in members:
                raise ValueError(
                    f"User {user_id} is not a member of this group"
                )

        # Get original ledger entries
        original_entries = (
            db.query(LedgerEntry)
            .filter(
                LedgerEntry.transaction_id == transaction_id
            )
            .all()
        )

        # Create reversal transaction
        reversal = Transaction(
    group_id=original.group_id,
    description=f"Reversal of transaction {transaction_id}",
    created_by=created_by,
    transaction_type="REVERSAL",
    reverses_transaction_id=transaction_id
)

        db.add(reversal)
        db.flush()

        # Reverse every original ledger entry
        for entry in original_entries:
            db.add(
                LedgerEntry(
                    transaction_id=reversal.id,
                    user_id=entry.user_id,
                    amount=-entry.amount
                )
            )

        # Create corrected transaction
        corrected = Transaction(
    group_id=original.group_id,
    description=description,
    created_by=created_by,
    transaction_type="EXPENSE",
    corrects_transaction_id=transaction_id
)

        db.add(corrected)
        db.flush()

        # Add corrected expense
        db.add(
            LedgerEntry(
                transaction_id=corrected.id,
                user_id=paid_by,
                amount=total
            )
        )

        for user_id, amount in splits.items():
            db.add(
                LedgerEntry(
                    transaction_id=corrected.id,
                    user_id=user_id,
                    amount=-amount
                )
            )

        db.commit()

        return corrected

    except Exception:
        db.rollback()
        raise


def create_settlement(
    db: Session,
    group_id: int,
    from_user: int,
    to_user: int,
    amount: Decimal,
):
    try:
        if amount <= 0:
            raise ValueError("Settlement amount must be positive")

        db.execute(
            select(Group)
            .where(Group.id == group_id)
            .with_for_update()
        )

        balances = get_balances(
            db,
            group_id
        )

        from_balance = balances.get(
            from_user,
            Decimal("0")
        )

        to_balance = balances.get(
            to_user,
            Decimal("0")
        )

        if from_balance >= 0:
            raise ValueError(
                "User does not owe money"
            )

        if to_balance <= 0:
            raise ValueError(
                "User is not owed money"
            )

        if amount > abs(from_balance):
            raise ValueError(
                "Settlement exceeds amount owed"
            )

        if amount > to_balance:
            raise ValueError(
                "Settlement exceeds amount receivable"
            )

        transaction = Transaction(
    group_id=group_id,
    description=f"Settlement: {from_user} -> {to_user}",
    created_by=from_user,
    transaction_type="SETTLEMENT"
)

        db.add(transaction)
        db.flush()

        db.add_all([
            LedgerEntry(
                transaction_id=transaction.id,
                user_id=from_user,
                amount=amount
            ),
            LedgerEntry(
                transaction_id=transaction.id,
                user_id=to_user,
                amount=-amount
            )
        ])

        db.commit()

        return transaction

    except Exception:
        db.rollback()
        raise