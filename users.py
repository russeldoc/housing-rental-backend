
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user
from database import get_db


router = APIRouter(prefix="/users", tags=["Users"])


# ---------- Response and request schemas ----------

class PaginatedUsersResponse(BaseModel):
    items: list[schemas.UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    phone_number: str | None = Field(default=None, min_length=7, max_length=20)
    family_members: int | None = Field(default=None, ge=1, le=50)
    home_district: str | None = Field(default=None, min_length=2, max_length=100)

    @field_validator(
        "full_name",
        "phone_number",
        "home_district",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


class UserStatusUpdate(BaseModel):
    is_active: bool


# ---------- Authorization ----------

def get_admin_user(
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage users.",
        )
    return current_user


# ---------- 1. Current user's profile ----------

@router.get("/me", response_model=schemas.UserResponse)
def get_my_profile(
    current_user: models.User = Depends(get_current_user),
):
    return current_user


# ---------- 2. Update current user's profile ----------

@router.patch("/me", response_model=schemas.UserResponse)
def update_my_profile(
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    updates = profile_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one profile field to update.",
        )

    # Explicit nulls are not allowed for these database fields.
    if any(value is None for value in updates.values()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Profile fields cannot be null.",
        )

    for field, value in updates.items():
        if isinstance(value, str) and not value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be empty.",
            )
        setattr(current_user, field, value)

    try:
        db.commit()
        db.refresh(current_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The profile update conflicts with existing data.",
        )

    return current_user


# ---------- 3. Admin lists and searches users ----------

@router.get("/", response_model=PaginatedUsersResponse)
def get_all_users(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    role: str | None = Query(default=None, pattern="^(admin|tenant)$"),
    is_active: bool | None = None,
    sort_by: str = Query(default="newest", pattern="^(newest|oldest)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    query = db.query(models.User)

    if search:
        term = f"%{search.strip()}%"
        search_filters = [
            models.User.full_name.ilike(term),
            models.User.email.ilike(term),
        ]

        if search.strip().isdigit():
            search_filters.append(
                models.User.id == int(search.strip())
            )

        from sqlalchemy import or_
        query = query.filter(or_(*search_filters))

    if role is not None:
        query = query.filter(models.User.role == role)

    if is_active is not None:
        query = query.filter(models.User.is_active.is_(is_active))

    if sort_by == "newest":
        query = query.order_by(
            models.User.created_at.desc(),
            models.User.id.desc(),
        )
    else:
        query = query.order_by(
            models.User.created_at.asc(),
            models.User.id.asc(),
        )

    total = query.count()
    items = (
        query
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size) if total else 0,
    }


# ---------- 4. Admin views one user ----------

@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


# ---------- 5. Admin activates/deactivates an account ----------

@router.patch("/{user_id}/status", response_model=schemas.UserResponse)
def update_user_status(
    user_id: int,
    status_data: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.id == admin.id and not status_data.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    user.is_active = status_data.is_active
    db.commit()
    db.refresh(user)

    return user
