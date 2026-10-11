from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import get_current_user
from ..services import get_group_for_member

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post("/", response_model=schemas.GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(
    data: schemas.GroupCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    group = models.Group(name=data.name, created_by=user.id)
    group.members.append(user)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/", response_model=List[schemas.GroupOut])
def my_groups(user: models.User = Depends(get_current_user)):
    return user.groups


@router.post("/{group_id}/members", response_model=schemas.GroupOut)
def add_member(
    group_id: int,
    data: schemas.MemberAdd,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    group = get_group_for_member(group_id, db, user)
    new_member = db.query(models.User).filter(models.User.username == data.username).first()
    if new_member is None:
        raise HTTPException(status_code=404, detail="User not found")
    if new_member in group.members:
        raise HTTPException(status_code=400, detail="User is already in this group")
    group.members.append(new_member)
    db.commit()
    db.refresh(group)
    return group
