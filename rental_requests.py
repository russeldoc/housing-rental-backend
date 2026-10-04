
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
import schemas
from auth import get_current_user
from database import get_db

router = APIRouter(
    prefix="/rental-requests",
    tags=["Rental Requests"],
)


def get_tenant_user(
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "tenant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenants can submit rental requests.",
        )
    return current_user


def get_admin_user(
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manage rental requests.",
        )
    return current_user


class RentalRequestStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"]


# 1. Tenant submits a rental request
@router.post(
    "/",
    response_model=schemas.RentalRequestDetailedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rental_request(
    request_data: schemas.RentalRequestCreate,
    db: Session = Depends(get_db),
    tenant: models.User = Depends(get_tenant_user),
):
    property_item = (
        db.query(models.Property)
        .filter(
            models.Property.id == request_data.property_id,
            models.Property.is_available.is_(True),
        )
        .first()
    )

    if property_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found or unavailable.",
        )

    existing_request = (
        db.query(models.RentalRequest)
        .filter(
            models.RentalRequest.tenant_id == tenant.id,
            models.RentalRequest.property_id == property_item.id,
            models.RentalRequest.status == "pending",
        )
        .first()
    )

    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending request for this property.",
        )

    new_request = models.RentalRequest(
        tenant_id=tenant.id,
        property_id=property_item.id,
        message=request_data.message,
        status="pending",
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    return new_request


# 2. Tenant views their own rental requests
@router.get(
    "/my",
    response_model=list[schemas.RentalRequestDetailedResponse],
)
def get_my_rental_requests(
    db: Session = Depends(get_db),
    tenant: models.User = Depends(get_tenant_user),
):
    return (
        db.query(models.RentalRequest)
        .filter(models.RentalRequest.tenant_id == tenant.id)
        .order_by(models.RentalRequest.id.desc())
        .all()
    )


# 3. Admin views all rental requests
@router.get(
    "/",
    response_model=list[schemas.RentalRequestDetailedResponse],
)
def get_all_rental_requests(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    return (
        db.query(models.RentalRequest)
        .order_by(models.RentalRequest.id.desc())
        .all()
    )


# 4. Admin approves or rejects a request
@router.patch(
    "/{request_id}/status",
    response_model=schemas.RentalRequestDetailedResponse,
)
def update_rental_request_status(
    request_id: int,
    status_data: RentalRequestStatusUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    rental_request = (
        db.query(models.RentalRequest)
        .filter(models.RentalRequest.id == request_id)
        .first()
    )

    if rental_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rental request not found.",
        )

    if rental_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This request has already been processed.",
        )

    if status_data.status == "approved":
        property_item = (
            db.query(models.Property)
            .filter(models.Property.id == rental_request.property_id)
            .with_for_update()
            .first()
        )

        if property_item is None or not property_item.is_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This property is no longer available.",
            )

        # Mark the property unavailable after approval.
        property_item.is_available = False

        # Reject other pending requests for this same property.
        other_pending_requests = (
            db.query(models.RentalRequest)
            .filter(
                models.RentalRequest.property_id == property_item.id,
                models.RentalRequest.id != rental_request.id,
                models.RentalRequest.status == "pending",
            )
            .all()
        )

        for other_request in other_pending_requests:
            other_request.status = "rejected"

    rental_request.status = status_data.status

    db.commit()
    db.refresh(rental_request)

    return rental_request
