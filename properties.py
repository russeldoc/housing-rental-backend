
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

import models
import schemas
from math import ceil
from typing import Literal

from database import get_db
from auth import get_current_user

class PaginatedPropertyResponse(BaseModel):
    items: list[schemas.PropertyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


router = APIRouter(
    prefix="/properties",
    tags=["Properties"],
)


def get_admin_user(
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage properties.",
        )
    return current_user


# 1. View all available properties
@router.get("/", response_model=PaginatedPropertyResponse)
def get_properties(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    property_id: int | None = Query(default=None, ge=1),
    min_rent: float | None = Query(default=None, ge=0),
    max_rent: float | None = Query(default=None, ge=0),
    is_available: bool = Query(default=True),
    sort_by: Literal[
        "newest",
        "title_asc",
        "price_asc",
        "price_desc",
    ] = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(models.Property)

    # Filter by availability.
    query = query.filter(
        models.Property.is_available.is_(is_available)
    )

    # Search by property title or location.
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            models.Property.title.ilike(search_term)
            | models.Property.location.ilike(search_term)
        )

    # Search for a specific property ID.
    if property_id is not None:
        query = query.filter(models.Property.id == property_id)

    # Filter by monthly rent.
    if min_rent is not None:
        query = query.filter(
            models.Property.monthly_rent >= min_rent
        )

    if max_rent is not None:
        query = query.filter(
            models.Property.monthly_rent <= max_rent
        )

    # Reject contradictory rent filters.
    if min_rent is not None and max_rent is not None:
        if min_rent > max_rent:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="min_rent cannot be greater than max_rent.",
            )

    # Count filtered results before pagination.
    total = query.count()

    # Apply sorting.
    if sort_by == "newest":
        query = query.order_by(
        models.Property.created_at.desc(),
        models.Property.id.desc(),
    )
    elif sort_by == "title_asc":
        query = query.order_by(
            models.Property.title.asc(),
            models.Property.id.asc(),
        )
    elif sort_by == "price_asc":
        query = query.order_by(
            models.Property.monthly_rent.asc(),
            models.Property.id.asc(),
        )
    elif sort_by == "price_desc":
        query = query.order_by(
            models.Property.monthly_rent.desc(),
            models.Property.id.desc(),
        )

    # Apply pagination.
    properties = (
        query
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": properties,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size) if total else 0,
    }


# 2. View one available property
@router.get("/{property_id}", response_model=schemas.PropertyResponse)
def get_property(
    property_id: int,
    db: Session = Depends(get_db),
):
    property_item = (
        db.query(models.Property)
        .filter(
            models.Property.id == property_id,
            models.Property.is_available.is_(True),
        )
        .first()
    )

    if property_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found or unavailable.",
        )

    return property_item


# 3. Create a property (admin only)
@router.post(
    "/",
    response_model=schemas.PropertyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_property(
    property_data: schemas.PropertyCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    new_property = models.Property(**property_data.model_dump())

    db.add(new_property)
    db.commit()
    db.refresh(new_property)

    return new_property


# 4. Update a property (admin only)
@router.put("/{property_id}", response_model=schemas.PropertyResponse)
def update_property(
    property_id: int,
    property_data: schemas.PropertyCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    property_item = (
        db.query(models.Property)
        .filter(models.Property.id == property_id)
        .first()
    )

    if property_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found.",
        )

    for field, value in property_data.model_dump().items():
        setattr(property_item, field, value)

    db.commit()
    db.refresh(property_item)

    return property_item


# 5. Delete a property (admin only)
@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    property_item = (
        db.query(models.Property)
        .filter(models.Property.id == property_id)
        .first()
    )

    if property_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found.",
        )

    # Preserve rental-request history.
    if property_item.rental_requests:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This property has rental requests and cannot be deleted. "
                "Set is_available to false instead."
            ),
        )

    db.delete(property_item)
    db.commit()

    return None
