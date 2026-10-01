from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String,
    ForeignKey,
    DateTime,
    Numeric,
    CheckConstraint,
    func,
    Enum
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp()
    )

    groups_created: Mapped[list["Group"]] = relationship(
        back_populates="creator"
    )

    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(
        back_populates="user"
    )


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp()
    )

    creator: Mapped["User"] = relationship(
        back_populates="groups_created"
    )


class GroupMember(Base):
    __tablename__ = "group_members"

    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id"),
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        primary_key=True
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id"),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    transaction_type: Mapped[str] = mapped_column(
        Enum(
            "EXPENSE",
            "REVERSAL",
            "SETTLEMENT",
            name="transaction_type"
        ),
        nullable=False,
        default="EXPENSE"
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp()
    )

    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(
        back_populates="transaction"
    )

    corrects_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=True
    )

    corrected_transaction: Mapped["Transaction | None"] = relationship(
        foreign_keys=[corrects_transaction_id],
        remote_side="Transaction.id"
    )

    reverses_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=True
    )

    reversed_transaction: Mapped["Transaction | None"] = relationship(
        foreign_keys=[reverses_transaction_id],
        remote_side="Transaction.id"
    )

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    transaction: Mapped["Transaction"] = relationship(
        back_populates="ledger_entries"
    )

    user: Mapped["User"] = relationship(
        back_populates="ledger_entries"
    )

    __table_args__ = (
        CheckConstraint(
            "amount <> 0",
            name="chk_ledger_entry_nonzero"
        ),
    )