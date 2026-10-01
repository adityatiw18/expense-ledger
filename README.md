# Expense Ledger

A ledger-based group expense splitting system built with **FastAPI, PostgreSQL, SQLAlchemy, React, and Docker**.

Expense Ledger is designed around an **immutable transaction ledger** rather than mutable user balances. Every financial operation is recorded as ledger entries, and balances are derived from the complete transaction history.

---

## Overview

Expense Ledger allows users to:

- Create expense groups
- Add members to groups
- Record shared expenses
- Track individual balances
- Generate settlements
- Correct previously recorded expenses
- Maintain an immutable financial history
- Safely handle concurrent financial operations
- Reconstruct balances directly from transaction history

The core design follows a **double-entry ledger model**, where every transaction produces ledger entries whose total equals zero.

---

# Architecture

```text
                    ┌─────────────────────┐
                    │    React Frontend   │
                    │                     │
                    │  Expense UI         │
                    │  Balance UI         │
                    │  Settlement UI      │
                    └──────────┬──────────┘
                               │
                               │ REST API
                               ▼
                    ┌─────────────────────┐
                    │    FastAPI Backend  │
                    │                     │
                    │  API Routes         │
                    │  Validation         │
                    │  Business Logic     │
                    └──────────┬──────────┘
                               │
                               │ SQLAlchemy
                               ▼
                    ┌─────────────────────┐
                    │     PostgreSQL      │
                    │                     │
                    │  Users              │
                    │  Groups             │
                    │  Transactions       │
                    │  Ledger Entries     │
                    └─────────────────────┘
```

---

# Core Ledger Model

Every financial transaction must balance to zero.

For example, suppose Alice pays ₹900 for herself, Bob and Charlie:

```text
Alice       +₹900
Bob         -₹300
Charlie     -₹600
------------------
Total          ₹0
```

The positive entry represents the person who paid.

The negative entries represent the users whose shares of the expense are owed.

The fundamental invariant is:

```text
SUM(transaction ledger entries) = 0
```

---

# Why a Ledger?

A traditional expense splitter might directly maintain balances:

```text
Alice     +₹500
Bob       -₹300
Charlie   -₹200
```

Every new expense would modify these stored balances.

Expense Ledger takes a different approach.

Instead of storing mutable balances, it stores the underlying financial transactions.

```text
Transaction
│
├── Alice     +₹500
├── Bob       -₹300
└── Charlie   -₹200
```

The balance is derived from the ledger:

```text
Balance(user) = SUM(all ledger entries for that user)
```

Therefore:

```text
Ledger → Source of Truth
Balance → Derived State
```

This makes it possible to reconstruct the current financial state directly from transaction history.

---

# Database Design

The main entities are:

```text
┌──────────┐
│  users   │
└────┬─────┘
     │
     ▼
┌────────────────┐
│ group_members  │
└───────┬────────┘
        │
        ▼
┌──────────────┐
│    groups    │
└───────┬──────┘
        │
        ▼
┌────────────────┐
│ transactions   │
└───────┬────────┘
        │
        ▼
┌─────────────────┐
│ ledger_entries  │
└─────────────────┘
```

## Users

```text
users
----------------
id
name
email
created_at
```

## Groups

```text
groups
----------------
id
name
created_by
created_at
```

## Group Members

```text
group_members
----------------
group_id
user_id
```

The combination of `group_id` and `user_id` forms the primary key.

## Transactions

```text
transactions
-------------------------------
id
group_id
description
transaction_type
created_by
created_at
corrects_transaction_id
reverses_transaction_id
```

Supported transaction types:

```text
EXPENSE
REVERSAL
SETTLEMENT
```

## Ledger Entries

```text
ledger_entries
----------------
id
transaction_id
user_id
amount
```

---

# Expense Creation

Suppose Alice pays ₹1200 for Alice, Bob and Charlie.

The expense is split as:

```text
Alice      ₹400
Bob        ₹400
Charlie    ₹400
```

The ledger records:

```text
Alice      +₹1200
Bob         -₹400
Charlie     -₹400
```

The remaining ₹400 is Alice's own share, so Alice's net position from this transaction is:

```text
Alice      +₹800
Bob         -₹400
Charlie     -₹400
------------------
Total          ₹0
```

The important invariant remains:

```text
+800 - 400 - 400 = 0
```

---

# Balance Calculation

Balances are derived using the ledger entries.

Conceptually:

```sql
SELECT
    user_id,
    SUM(amount)
FROM ledger_entries
GROUP BY user_id;
```

For example:

```text
Alice       +₹500
Bob         -₹300
Charlie     -₹200
```

means:

```text
Alice is owed ₹500
Bob owes ₹300
Charlie owes ₹200
```

The balance is therefore a **derived value**, not the source of truth.

---

# Settlements

Once balances are calculated, the system determines how users can settle their debts.

For example:

```text
Alice       +₹500
Bob         -₹300
Charlie     -₹200
```

can produce:

```text
Bob     → Alice     ₹300
Charlie → Alice     ₹200
```

A settlement is itself recorded as a transaction.

For:

```text
Bob → Alice ₹300
```

the ledger records:

```text
Bob       +₹300
Alice     -₹300
----------------
Total        ₹0
```

This means settlements become part of the same ledger history as expenses.

---

# Expense Corrections

Financial history is not overwritten.

Suppose the original expense is:

```text
Alice      +₹900
Bob        -₹450
Charlie    -₹450
```

If the expense was entered incorrectly, the original transaction is not edited.

Instead, the system creates a reversal:

```text
Alice      -₹900
Bob        +₹450
Charlie    +₹450
```

Then a new corrected expense is created.

The history becomes:

```text
Original Expense
       │
       ▼
   Reversal
       │
       ▼
Corrected Expense
```

This preserves an audit trail.

---

# Self-Referencing Transactions

Transactions can reference other transactions through:

```text
corrects_transaction_id
reverses_transaction_id
```

This creates relationships such as:

```text
Transaction 10
     │
     │ corrected by
     ▼
Transaction 15
```

or:

```text
Transaction 10
     │
     │ reversed by
     ▼
Transaction 14
```

These are implemented using self-referencing foreign keys.

---

# Database Transactions

Financial operations are executed inside database transactions.

The general pattern is:

```python
try:
    # create transaction
    # create ledger entries

    db.commit()

except Exception:
    db.rollback()
    raise
```

This ensures that a financial operation is treated as one atomic unit.

For example:

```text
Create Transaction
        +
Create Ledger Entries
        ↓
      COMMIT
```

If something fails:

```text
Create Transaction
        +
Create Ledger Entries
        ↓
     ERROR
        ↓
    ROLLBACK
```

This prevents partially completed financial operations.

---

# Concurrency Control

Financial operations can be affected by concurrent requests.

For example, two settlement requests could arrive at nearly the same time for the same group.

The system locks the group row:

```python
select(Group).where(
    Group.id == group_id
).with_for_update()
```

This uses PostgreSQL row-level locking.

Conceptually:

```text
Request A
   │
   ├── Lock Group
   │
   ├── Calculate balance
   │
   ├── Create settlement
   │
   └── Commit
             │
             ▼
        Lock released
             │
             ▼
Request B can continue
```

This prevents conflicting financial operations on the same group from independently modifying the group's financial state.

---

# SQLAlchemy

The backend uses SQLAlchemy as the ORM.

Database tables are represented as Python models.

Example:

```python
class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id"),
        nullable=False
    )
```

SQLAlchemy is used for:

- ORM models
- Foreign keys
- Relationships
- Queries
- Filtering
- Joins
- Aggregations
- Transactions
- Row-level locking

---

# FastAPI

The backend exposes REST APIs using FastAPI.

Example:

```python
@app.get("/groups/{group_id}/balances")
def group_balances(
    group_id: int,
    db: Session = Depends(get_db)
):
    ...
```

FastAPI provides:

- HTTP routing
- Request validation
- Dependency injection
- JSON responses
- Automatic API documentation

---

# API Endpoints

## Users

```text
POST /users
```

Creates a user.

## Groups

```text
POST /groups
POST /groups/{group_id}/members
GET  /groups/{group_id}
GET  /users/{user_id}/groups
```

Used for creating and managing expense groups.

## Expenses

```text
POST /groups/{group_id}/expenses
PUT  /transactions/{transaction_id}/correct
```

Used for creating and correcting expenses.

## Balances

```text
GET /groups/{group_id}/balances
```

Returns the calculated balances for all members.

## Settlements

```text
GET  /groups/{group_id}/settlements
POST /groups/{group_id}/settlements
```

Used to calculate and record settlements.

## Transactions

```text
GET /groups/{group_id}/transactions
GET /transactions/{transaction_id}
```

Used to view transaction history and transaction details.

---

# Testing

The project uses **pytest** for automated testing.

Tests cover:

- API endpoints
- Expense creation
- Balance calculation
- Expense correction
- Settlement calculation
- Settlement creation
- Database behavior
- Error handling

Run the complete test suite:

```bash
pytest
```

Current test suite:

```text
47 passed
```

---

# Database Migrations

Database schema changes are managed using **Alembic**.

Create a migration:

```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:

```bash
alembic upgrade head
```

This allows the database schema to evolve without manually recreating the database.

---

# Docker

The application can be run using Docker Compose.

Start the complete application:

```bash
docker compose up --build
```

The backend will be available at:

```text
http://localhost:8000
```

PostgreSQL runs as a separate Docker service.

The backend runs database migrations when the container starts.

---

# Running Locally

## Backend

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

---

# Project Structure

```text
expense-ledger/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   │
│   ├── services/
│   │   ├── balance_service.py
│   │   ├── ledger_service.py
│   │   └── settlement_service.py
│   │
│   └── tests/
│       ├── conftest.py
│       ├── test_api.py
│       ├── test_ledger.py
│       └── test_settlement.py
│
├── alembic/
│   └── versions/
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── pages/
│   │       └── CreateLedger.jsx
│   │
│   ├── public/
│   ├── package.json
│   └── Dockerfile
│
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pytest.ini
├── requirements.txt
└── .gitignore
```

---

# Key Design Decisions

## 1. Ledger Instead of Stored Balances

Balances are derived from ledger entries rather than stored as mutable values.

```text
Ledger
  ↓
Source of Truth
  ↓
Balance
  ↓
Settlement
```

## 2. Immutable Financial History

Transactions are not overwritten.

Corrections are represented using:

```text
Original Transaction
        ↓
     Reversal
        ↓
Corrected Transaction
```

This preserves an audit trail.

## 3. Settlements Are Transactions

Settlements are recorded in the same ledger as expenses.

```text
Expenses
   +
Corrections
   +
Settlements
   ↓
Complete Financial History
```

## 4. Database Transactions

Financial operations use commit/rollback semantics to ensure atomic updates.

## 5. Concurrency Protection

Group-level row locking is used for operations that modify group financial state.

```text
SELECT ... FOR UPDATE
```

## 6. Derived State

The application avoids storing values that can be reliably reconstructed from source data.

```text
Transaction History
        ↓
   Balance Calculation
        ↓
     Settlements
```

---

# Tech Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic

### Frontend

- React
- Vite
- JavaScript
- CSS

### Testing

- pytest

### Infrastructure

- Docker
- Docker Compose

---

# What This Project Demonstrates

This project was built to explore backend engineering concepts beyond basic CRUD applications.

Key concepts include:

- REST API design
- FastAPI dependency injection
- SQLAlchemy ORM
- PostgreSQL relational modelling
- Foreign keys and constraints
- Self-referencing relationships
- Database transactions
- Commit and rollback
- Row-level locking
- Concurrency control
- Connection pooling
- Immutable financial records
- Double-entry ledger modelling
- Derived state
- Settlement algorithms
- Database migrations
- Automated testing
- Docker containerization
- React state management

---

# Future Improvements

Potential improvements include:

- Authentication and authorization
- User accounts and sessions
- Pagination for transaction history
- Better settlement optimization
- Transaction search and filtering
- Expense categories
- Recurring expenses
- Notifications
- Production deployment
- Monitoring and logging

---

## Author

**Aditya Tiwari**

Built as a backend-focused portfolio project to explore financial data modelling, database consistency, concurrency, and full-stack application development.
