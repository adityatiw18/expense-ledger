from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import LedgerEntry, Transaction


def get_balances(
    db: Session,
    group_id: int
):
    results = (
        db.query(
            LedgerEntry.user_id,
            func.sum(
                LedgerEntry.amount
            ).label("balance")
        )
        .join(Transaction)
        .filter(
            Transaction.group_id == group_id
        )
        .group_by(
            LedgerEntry.user_id
        )
        .all()
    )

    return {
        user_id: balance
        for user_id, balance in results
    }