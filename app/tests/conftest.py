import pytest
import uuid

from app.database import SessionLocal
from app.models import (
    User,
    Group,
    GroupMember,
    Transaction,
    LedgerEntry
)


@pytest.fixture
def db():
    session = SessionLocal()

    yield session

    session.rollback()
    session.close()


@pytest.fixture
def test_data():
    db = SessionLocal()

    user1 = User(
        name="Test User 1",
        email=f"pytest-user1-{uuid.uuid4()}@example.com"
    )

    user2 = User(
        name="Test User 2",
        email=f"pytest-user2-{uuid.uuid4()}@example.com"
    )

    user3 = User(
        name="Test User 3",
        email=f"pytest-user3-{uuid.uuid4()}@example.com"
    )

    db.add_all([
        user1,
        user2,
        user3
    ])

    db.flush()

    group = Group(
        name="PYTEST - Expense Ledger",
        created_by=user1.id
    )

    db.add(group)
    db.flush()

    db.add_all([
        GroupMember(
            group_id=group.id,
            user_id=user1.id
        ),
        GroupMember(
            group_id=group.id,
            user_id=user2.id
        ),
        GroupMember(
            group_id=group.id,
            user_id=user3.id
        )
    ])

    db.commit()
    
    data = {
        "group_id": group.id,
        "user1": user1.id,
        "user2": user2.id,
        "user3": user3.id
    }
    db.close()
    yield data

    user_ids = [
        user1.id,
        user2.id,
        user3.id
    ]

    cleanup_db = SessionLocal()

    groups = (
        cleanup_db.query(Group)
        .filter(Group.created_by.in_(user_ids))
        .all()
    )

    group_ids = [
        group.id
        for group in groups
    ]

    if group_ids:
        transactions = (
            cleanup_db.query(Transaction)
            .filter(Transaction.group_id.in_(group_ids))
            .all()
        )

        transaction_ids = [
            transaction.id
            for transaction in transactions
        ]

        if transaction_ids:
            cleanup_db.query(LedgerEntry).filter(
                LedgerEntry.transaction_id.in_(transaction_ids)
            ).delete(
                synchronize_session=False
            )

            cleanup_db.query(Transaction).filter(
                Transaction.id.in_(transaction_ids)
            ).delete(
                synchronize_session=False
            )

        cleanup_db.query(GroupMember).filter(
            GroupMember.group_id.in_(group_ids)
        ).delete(
            synchronize_session=False
        )

        cleanup_db.query(Group).filter(
            Group.id.in_(group_ids)
        ).delete(
            synchronize_session=False
        )

    cleanup_db.query(User).filter(
        User.id.in_(user_ids)
    ).delete(
        synchronize_session=False
    )

    cleanup_db.commit()
    cleanup_db.close()