from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import get_current_user
from ..services import (
    calculate_balances,
    get_group_for_member,
    simplify_debts,
    split_equally,
    to_expense_out,
)

router = APIRouter(prefix="/groups", tags=["Expenses"])


@router.post(
    "/{group_id}/expenses",
    response_model=schemas.ExpenseOut,
    status_code=status.HTTP_201_CREATED,
)
def add_expense(
    group_id: int,
    data: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    group = get_group_for_member(group_id, db, user)

    if data.split_among:
        wanted = set(data.split_among)
        participants = [m for m in group.members if m.username in wanted]
        if len(participants) != len(wanted):
            raise HTTPException(
                status_code=400, detail="split_among contains users who are not in this group"
            )
    else:
        participants = list(group.members)

    total = round(data.amount * 100)  # rupees to paise
    shares = split_equally(total, len(participants))

    expense = models.Expense(
        description=data.description, amount=total, paid_by=user.id, group_id=group.id
    )
    for person, share in zip(participants, shares):
        expense.splits.append(models.ExpenseSplit(user_id=person.id, share=share))

    db.add(expense)
    db.commit()
    db.refresh(expense)
    return to_expense_out(expense)


@router.get("/{group_id}/expenses", response_model=List[schemas.ExpenseOut])
def list_expenses(
    group_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    group = get_group_for_member(group_id, db, user)
    return [to_expense_out(e) for e in group.expenses]


@router.delete("/{group_id}/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    group_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    group = get_group_for_member(group_id, db, user)
    expense = (
        db.query(models.Expense)
        .filter(models.Expense.id == expense_id, models.Expense.group_id == group.id)
        .first()
    )
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.paid_by != user.id:
        raise HTTPException(status_code=403, detail="Only the person who paid can delete this expense")
    db.delete(expense)
    db.commit()


@router.get("/{group_id}/balances", response_model=List[schemas.BalanceOut])
def balances(
    group_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    group = get_group_for_member(group_id, db, user)
    names = {m.id: m.username for m in group.members}
    net = calculate_balances(group)
    return [{"username": names[uid], "balance": amount / 100} for uid, amount in net.items()]


@router.get("/{group_id}/settle", response_model=List[schemas.SettlementOut])
def settle_up(
    group_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    group = get_group_for_member(group_id, db, user)
    names = {m.id: m.username for m in group.members}
    payments = simplify_debts(calculate_balances(group))
    return [
        {"payer": names[payer], "receiver": names[receiver], "amount": amount / 100}
        for payer, receiver, amount in payments
    ]
