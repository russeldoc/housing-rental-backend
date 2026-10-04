
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from auth import get_current_user

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
@router.get("/", response_model=list[schemas.PropertyResponse])
def get_properties(db: Session = Depends(get_db)):
    return (
        db.query(models.Property)
        .filter(models.Property.is_available.is_(True))
        .order_by(models.Property.id.desc())
        .all()
    )


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
