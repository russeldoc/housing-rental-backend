
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
from typing import Optional
from decimal import Decimal
from datetime import datetime


# ==========================================
# USER REGISTRATION
# ==========================================
class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone_number: str = Field(min_length=7, max_length=20)
    family_members: int = Field(ge=1)
    home_district: str = Field(min_length=2, max_length=100)

    national_id: Optional[str] = Field(
        default=None, min_length=1, max_length=50
    )
    passport_number: Optional[str] = Field(
        default=None, min_length=1, max_length=50
    )

    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_identity_document(self):
        national_id = (
            self.national_id.strip() if self.national_id else None
        )
        passport = (
            self.passport_number.strip()
            if self.passport_number else None
        )

        if not national_id and not passport:
            raise ValueError(
                "Provide either a National ID or a passport number."
            )

        self.national_id = national_id
        self.passport_number = passport
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
    description: str = Field(min_length=5)
    location: str = Field(min_length=2, max_length=255)
    monthly_rent: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    bedrooms: int = Field(default=1, ge=1)
    bathrooms: int = Field(default=1, ge=1)
    image_url: Optional[str] = Field(default=None, max_length=500)


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
    message: Optional[str] = Field(default=None, max_length=2000)


# ==========================================
# RENTAL REQUEST RESPONSE
# ==========================================
class RentalRequestResponse(BaseModel):
    id: int
    tenant_id: int
    property_id: int
    message: Optional[str]
    status: str

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
    status: str
    created_at: datetime
    tenant: TenantSummary
    property: PropertySummary

    model_config = ConfigDict(from_attributes=True)

