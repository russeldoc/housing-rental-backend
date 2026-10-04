
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


# ==========================================
# USER REGISTRATION
# ==========================================

class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone_number: str = Field(min_length=7, max_length=20)
    family_members: int = Field(ge=1, le=50)
    home_district: str = Field(min_length=2, max_length=100)

    national_id: Optional[str] = Field(
        default=None, min_length=1, max_length=50
    )
    passport_number: Optional[str] = Field(
        default=None, min_length=1, max_length=50
    )

    password: str = Field(min_length=8, max_length=128)

    @field_validator(
        "full_name",
        "phone_number",
        "home_district",
        mode="before",
    )
    @classmethod
    def strip_required_strings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator(
        "national_id",
        "passport_number",
        mode="before",
    )
    @classmethod
    def clean_identity_documents(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if not value.strip():
            raise ValueError("Password cannot contain only spaces.")
        return value

    @model_validator(mode="after")
    def validate_identity_document(self):
        if not self.national_id and not self.passport_number:
            raise ValueError(
                "Provide either a National ID or a passport number."
            )
        return self


# ==========================================
# USER RESPONSE
# ==========================================

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: str
    family_members: int
    home_district: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# PROPERTY CREATION
# ==========================================

class PropertyCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=5000)
    location: str = Field(min_length=2, max_length=255)
    monthly_rent: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
    )
    bedrooms: int = Field(default=1, ge=1, le=100)
    bathrooms: int = Field(default=1, ge=1, le=100)
    image_url: Optional[str] = Field(
        default=None,
        max_length=500,
    )

    @field_validator("title", "description", "location", mode="before")
    @classmethod
    def strip_property_strings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("image_url", mode="before")
    @classmethod
    def clean_image_url(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


# ==========================================
# PROPERTY RESPONSE
# ==========================================

class PropertyResponse(PropertyCreate):
    id: int
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# RENTAL REQUEST CREATION
# ==========================================

class RentalRequestCreate(BaseModel):
    property_id: int = Field(gt=0)
    message: Optional[str] = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("message", mode="before")
    @classmethod
    def clean_message(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


# ==========================================
# RENTAL REQUEST RESPONSE
# ==========================================

class RentalRequestResponse(BaseModel):
    id: int
    tenant_id: int
    property_id: int
    message: Optional[str]
    status: Literal["pending", "approved", "rejected"]

    model_config = ConfigDict(from_attributes=True)


class TenantSummary(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone_number: str
    home_district: str
    family_members: int

    model_config = ConfigDict(from_attributes=True)


class PropertySummary(BaseModel):
    id: int
    title: str
    location: str
    monthly_rent: Decimal
    bedrooms: int
    bathrooms: int
    image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RentalRequestDetailedResponse(BaseModel):
    id: int
    tenant_id: int
    property_id: int
    message: Optional[str] = None
    status: Literal["pending", "approved", "rejected"]
    created_at: datetime
    tenant: TenantSummary
    property: PropertySummary

    model_config = ConfigDict(from_attributes=True)
