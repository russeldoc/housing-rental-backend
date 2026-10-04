
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import relationship

from database import Base


# ==========================================
# 1. USERS TABLE
# ==========================================
class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "national_id IS NOT NULL OR passport_number IS NOT NULL",
            name="check_user_identity_document",
        ),
        CheckConstraint(
            "family_members >= 1",
            name="check_family_members_positive",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Personal information
    full_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone_number = Column(String(20), nullable=False)
    family_members = Column(Integer, nullable=False)
    home_district = Column(String(100), nullable=False)

    # National ID or passport (at least one required)
    national_id = Column(String(50), unique=True, nullable=True)
    passport_number = Column(String(50), unique=True, nullable=True)

    # Authentication and account information
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="tenant", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship with rental requests
    rental_requests = relationship(
        "RentalRequest",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )


# ==========================================
# 2. PROPERTIES TABLE
# ==========================================
class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(255), nullable=False)
    monthly_rent = Column(Numeric(10, 2), nullable=False)

    bedrooms = Column(Integer, default=1, nullable=False)
    bathrooms = Column(Integer, default=1, nullable=False)

    image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship with rental requests
    rental_requests = relationship(
        "RentalRequest",
        back_populates="property",
        cascade="all, delete-orphan",
    )


# ==========================================
# 3. RENTAL REQUESTS TABLE
# ==========================================
class RentalRequest(Base):
    __tablename__ = "rental_requests"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    property_id = Column(
        Integer,
        ForeignKey("properties.id"),
        nullable=False,
        index=True,
    )

    message = Column(Text, nullable=True)

    status = Column(
        String(20),
        default="pending",
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    tenant = relationship(
        "User",
        back_populates="rental_requests",
    )

    property = relationship(
        "Property",
        back_populates="rental_requests",
    )
