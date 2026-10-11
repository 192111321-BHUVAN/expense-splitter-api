from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=6)


class UserOut(BaseModel):
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class GroupCreate(BaseModel):
    name: str = Field(min_length=1)


class MemberAdd(BaseModel):
    username: str


class GroupOut(BaseModel):
    id: int
    name: str
    members: List[UserOut]
    model_config = ConfigDict(from_attributes=True)


class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1)
    amount: float = Field(gt=0, description="Amount in rupees")
    split_among: Optional[List[str]] = Field(
        default=None,
        description="Usernames to split with. Leave empty to split with the whole group.",
    )


class SplitOut(BaseModel):
    username: str
    share: float


class ExpenseOut(BaseModel):
    id: int
    description: str
    amount: float
    paid_by: str
    splits: List[SplitOut]
    created_at: datetime


class BalanceOut(BaseModel):
    username: str
    balance: float  # positive = should receive, negative = owes


class SettlementOut(BaseModel):
    payer: str
    receiver: str
    amount: float
