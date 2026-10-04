
from math import ceil
from datetime import date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

import models
import schemas
from auth import get_current_user
from database import get_db


router = APIRouter(
    prefix="/rental-requests",
    tags=["Rental Requests"],
)


# ---------- Pagination response ----------

class PaginatedRentalRequestResponse(BaseModel):
    items: list[schemas.RentalRequestDetailedResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------- Authorization ----------

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


# ---------- Shared date filtering ----------

def apply_date_filters(query, start_date, end_date):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date cannot be after end_date.",
        )

    if start_date:
        start_datetime = datetime.combine(start_date, time.min)
        query = query.filter(
            models.RentalRequest.created_at >= start_datetime
        )

    if end_date:
        # Include the entire end date.
        end_datetime = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
        )
        query = query.filter(
            models.RentalRequest.created_at < end_datetime
        )

    return query


# ---------- Shared pagination response ----------

def paginate_requests(query, page, page_size, sort_by):
    if sort_by == "newest":
        query = query.order_by(
            models.RentalRequest.created_at.desc(),
            models.RentalRequest.id.desc(),
        )
    else:
        query = query.order_by(
            models.RentalRequest.created_at.asc(),
            models.RentalRequest.id.asc(),
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


# ---------- 1. Tenant submits a rental request ----------

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


# ---------- 2. Tenant views their own requests ----------

@router.get(
    "/my",
    response_model=PaginatedRentalRequestResponse,
)
def get_my_rental_requests(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    request_status: Literal["pending", "approved", "rejected"] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    sort_by: Literal["newest", "oldest"] = "newest",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant: models.User = Depends(get_tenant_user),
):
    query = db.query(models.RentalRequest).filter(
        models.RentalRequest.tenant_id == tenant.id
    )

    if search:
        search_term = f"%{search.strip()}%"
        search_filters = [
            models.Property.title.ilike(search_term)
        ]

        if search.strip().isdigit():
            search_filters.append(
                models.RentalRequest.id == int(search.strip())
            )

        query = query.join(
            models.Property,
            models.RentalRequest.property_id == models.Property.id,
        ).filter(or_(*search_filters))

    if request_status:
        query = query.filter(
            models.RentalRequest.status == request_status
        )

    query = apply_date_filters(query, start_date, end_date)

    return paginate_requests(query, page, page_size, sort_by)


# ---------- 3. Admin views all rental requests ----------

@router.get(
    "/",
    response_model=PaginatedRentalRequestResponse,
)
def get_all_rental_requests(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    request_status: Literal["pending", "approved", "rejected"] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    sort_by: Literal["newest", "oldest"] = "newest",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
):
    query = db.query(models.RentalRequest)

    if search:
        search_term = f"%{search.strip()}%"

        query = (
            query
            .join(
                models.User,
                models.RentalRequest.tenant_id == models.User.id,
            )
            .join(
                models.Property,
                models.RentalRequest.property_id == models.Property.id,
            )
        )

        search_filters = [
            models.User.full_name.ilike(search_term),
            models.User.email.ilike(search_term),
            models.Property.title.ilike(search_term),
        ]

        if search.strip().isdigit():
            search_filters.append(
                models.RentalRequest.id == int(search.strip())
            )

        query = query.filter(or_(*search_filters))

    if request_status:
        query = query.filter(
            models.RentalRequest.status == request_status
        )

    query = apply_date_filters(query, start_date, end_date)

    return paginate_requests(query, page, page_size, sort_by)


# ---------- 4. Admin approves or rejects a request ----------

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

        property_item.is_available = False

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
