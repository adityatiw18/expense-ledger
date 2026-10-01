from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import User, Group, GroupMember, Transaction, LedgerEntry#from .models import IntegrityError
from .schemas import (
    UserCreate,
    UserResponse,
    ExpenseRequest,
    ExpenseResponse,
    SettlementResponse,
    SettlementRequest,
    GroupCreate,
    MemberCreate,
    GroupDetailsResponse,
    GroupMemberResponse,
    GroupResponse,
    CorrectionRequest
)
from .services.ledger_service import (
    create_expense,
    correct_expense,
    create_settlement
)
from .services.balance_service import get_balances
from .services.settlement_service import get_group_settlements


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

@app.get("/transactions/{transaction_id}")
def transaction_details(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id)
        .first()
    )

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found"
        )

    entries = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.transaction_id == transaction_id)
        .all()
    )

    return {
        "id": transaction.id,
        "description": transaction.description,
        "created_by": transaction.created_by,
        "created_at": transaction.created_at,
        "transaction_type": transaction.transaction_type,
        "amount": max(
            [entry.amount for entry in entries if entry.amount > 0],
            default=0
        ),
        "entries": [
            {
                "user_id": entry.user_id,
                "amount": entry.amount
            }
            for entry in entries
        ]
    }

@app.get("/groups/{group_id}/transactions")
def group_transactions(
    group_id: int,
    db: Session = Depends(get_db)
):
    transactions = (
        db.query(Transaction)
        .filter(Transaction.group_id == group_id)
        .order_by(
            Transaction.created_at.desc(),
            Transaction.id.desc()
        )
        .all()
    )

    result = []

    for transaction in transactions:
        entries = (
            db.query(LedgerEntry)
            .filter(
                LedgerEntry.transaction_id == transaction.id
            )
            .all()
        )

        display_description = transaction.description

        # Show names instead of IDs for settlements
        if transaction.transaction_type == "SETTLEMENT":
            positive_entry = next(
                (entry for entry in entries if entry.amount > 0),
                None
            )

            negative_entry = next(
                (entry for entry in entries if entry.amount < 0),
                None
            )

            if positive_entry and negative_entry:
                from_user = (
                    db.query(User)
                    .filter(User.id == positive_entry.user_id)
                    .first()
                )

                to_user = (
                    db.query(User)
                    .filter(User.id == negative_entry.user_id)
                    .first()
                )

                if from_user and to_user:
                    display_description = (
                        f"Settlement: {from_user.name} → {to_user.name}"
                    )

        # The positive ledger entry represents who paid
        positive_entry = next(
            (entry for entry in entries if entry.amount > 0),
            None
        )

        paid_by = (
            positive_entry.user_id
            if positive_entry
            else None
        )

        amount = (
            positive_entry.amount
            if positive_entry
            else 0
        )

        result.append({
            "id": transaction.id,
            "description": display_description,
            "created_by": transaction.created_by,
            "paid_by": paid_by,
            "created_at": transaction.created_at,
            "transaction_type": transaction.transaction_type,
            "amount": amount
        })

    return result

@app.post(
    "/users",
    response_model=UserResponse,
    status_code=201
)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    new_user = User(
        name=user.name,
        email=user.email
    )

    db.add(new_user)

    try:
        db.commit()
        db.refresh(new_user)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    return new_user


@app.post(
    "/groups/{group_id}/expenses",
    response_model=ExpenseResponse,
    status_code=201
)
def add_expense(
    group_id: int,
    expense: ExpenseRequest,
    db: Session = Depends(get_db)
):
    try:
        transaction = create_expense(
            db=db,
            group_id=group_id,
            description=expense.description,
            created_by=expense.created_by,
            paid_by=expense.paid_by,
            splits=expense.splits
        )

        return ExpenseResponse(
            transaction_id=transaction.id,
            description=transaction.description
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@app.put("/transactions/{transaction_id}/correct")
def correct_transaction(
    transaction_id: int,
    request: CorrectionRequest,
    db: Session = Depends(get_db)
):
    try:
        transaction = correct_expense(
            db=db,
            transaction_id=transaction_id,
            created_by=request.created_by,
            description=request.description,
            paid_by=request.paid_by,
            splits=request.splits
        )

        return {
            "transaction_id": transaction.id,
            "description": transaction.description
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    
@app.get(
    "/groups/{group_id}/balances"
)
def group_balances(
    group_id: int,
    db: Session = Depends(get_db)
):
    return get_balances(
        db,
        group_id
    )


@app.get(
    "/groups/{group_id}/settlements",
    response_model=list[SettlementResponse]
)
def group_settlements(
    group_id: int,
    db: Session = Depends(get_db)
):
    settlements = get_group_settlements(
        db,
        group_id
    )

    return [
        SettlementResponse(
            from_user=payer,
            to_user=receiver,
            amount=amount
        )
        for payer, receiver, amount in settlements
    ]

@app.post("/groups/{group_id}/settlements", status_code=201)
def create_group_settlement(
    group_id: int,
    settlement: SettlementRequest,
    db: Session = Depends(get_db)
):
    try:
        transaction = create_settlement(
            db=db,
            group_id=group_id,
            from_user=settlement.from_user,
            to_user=settlement.to_user,
            amount=settlement.amount
        )

        return {
            "transaction_id": transaction.id,
            "from_user": settlement.from_user,
            "to_user": settlement.to_user,
            "amount": settlement.amount
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@app.post(
    "/groups",
    response_model=GroupResponse,
    status_code=201
)
def create_group(
    group: GroupCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.id == group.created_by
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    new_group = Group(
        name=group.name,
        created_by=group.created_by
    )

    db.add(new_group)
    db.flush()

    db.add(
        GroupMember(
            group_id=new_group.id,
            user_id=group.created_by
        )
    )

    db.commit()
    db.refresh(new_group)

    return new_group


@app.post(
    "/groups/{group_id}/members",
    status_code=201
)
def add_member(
    group_id: int,
    member: MemberCreate,
    db: Session = Depends(get_db)
):
    group = db.query(Group).filter(
        Group.id == group_id
    ).first()

    if not group:
        raise HTTPException(
            status_code=404,
            detail="Group not found"
        )

    user = db.query(User).filter(
        User.id == member.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    existing_member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == member.user_id
    ).first()

    if existing_member:
        raise HTTPException(
            status_code=400,
            detail="User is already a member"
        )

    new_member = GroupMember(
        group_id=group_id,
        user_id=member.user_id
    )

    db.add(new_member)
    db.commit()

    return {
        "message": "Member added successfully"
    }


@app.get(
    "/groups/{group_id}",
    response_model=GroupDetailsResponse
)
def get_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    group = db.query(Group).filter(
        Group.id == group_id
    ).first()

    if not group:
        raise HTTPException(
            status_code=404,
            detail="Group not found"
        )

    members = (
        db.query(User)
        .join(
            GroupMember,
            GroupMember.user_id == User.id
        )
        .filter(
            GroupMember.group_id == group_id
        )
        .all()
    )

    return GroupDetailsResponse(
        id=group.id,
        name=group.name,
        created_by=group.created_by,
        members=[
            GroupMemberResponse(
                id=user.id,
                name=user.name,
                email=user.email
            )
            for user in members
        ]
    )

@app.get("/users/{user_id}/groups")
def user_groups(
    user_id: int,
    db: Session = Depends(get_db)
):
    groups = (
        db.query(Group)
        .join(
            GroupMember,
            GroupMember.group_id == Group.id
        )
        .filter(GroupMember.user_id == user_id)
        .order_by(Group.created_at.desc())
        .all()
    )

    return [
        {
            "id": group.id,
            "name": group.name,
            "created_at": group.created_at,
        }
        for group in groups
    ]