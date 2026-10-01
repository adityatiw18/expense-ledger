from decimal import Decimal

from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    email: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str


class ExpenseRequest(BaseModel):
    description: str
    created_by: int
    paid_by: int
    splits: dict[int, Decimal]

class CorrectionRequest(BaseModel):
    description: str
    created_by: int
    paid_by: int
    splits: dict[int, Decimal]

class ExpenseResponse(BaseModel):
    transaction_id: int
    description: str


class SettlementResponse(BaseModel):
    from_user: int
    to_user: int
    amount: Decimal


class GroupCreate(BaseModel):
    name: str
    created_by: int


class GroupResponse(BaseModel):
    id: int
    name: str
    created_by: int

class MemberCreate(BaseModel):
    user_id: int

class GroupMemberResponse(BaseModel):
    id: int
    name: str
    email: str


class GroupDetailsResponse(BaseModel):
    id: int
    name: str
    created_by: int
    members: list[GroupMemberResponse]

class SettlementRequest(BaseModel):
    from_user: int
    to_user: int
    amount: Decimal