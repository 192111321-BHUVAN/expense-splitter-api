from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models


def get_group_for_member(group_id: int, db: Session, user: models.User) -> models.Group:
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    if user not in group.members:
        raise HTTPException(status_code=403, detail="You are not a member of this group")
    return group


def split_equally(total: int, n: int) -> list[int]:
    """Split `total` paise among `n` people. The shares always add up to `total`."""
    base, remainder = divmod(total, n)
    return [base + 1 if i < remainder else base for i in range(n)]


def calculate_balances(group: models.Group) -> dict[int, int]:
    """Net balance per user id in paise. Positive = should receive, negative = owes."""
    net = {member.id: 0 for member in group.members}
    for expense in group.expenses:
        net[expense.paid_by] += expense.amount
        for split in expense.splits:
            net[split.user_id] -= split.share
    return net


def simplify_debts(balances: dict[int, int]) -> list[tuple[int, int, int]]:
    """Return (payer_id, receiver_id, amount) payments that settle every balance."""
    creditors = [[amount, uid] for uid, amount in balances.items() if amount > 0]
    debtors = [[-amount, uid] for uid, amount in balances.items() if amount < 0]
    creditors.sort(reverse=True)
    debtors.sort(reverse=True)

    payments = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        pay = min(debtors[i][0], creditors[j][0])
        payments.append((debtors[i][1], creditors[j][1], pay))
        debtors[i][0] -= pay
        creditors[j][0] -= pay
        if debtors[i][0] == 0:
            i += 1
        if creditors[j][0] == 0:
            j += 1
    return payments


def to_expense_out(expense: models.Expense) -> dict:
    return {
        "id": expense.id,
        "description": expense.description,
        "amount": expense.amount / 100,
        "paid_by": expense.payer.username,
        "splits": [
            {"username": s.user.username, "share": s.share / 100} for s in expense.splits
        ],
        "created_at": expense.created_at,
    }
