
from fastapi import FastAPI
from sqlalchemy import text

from database import engine, Base
import models
from auth import router as auth_router
from properties import router as properties_router
from rental_requests import router as rental_requests_router


app = FastAPI(
    title="HomeRent API",
    description="Backend API for HomeRent",
    version="1.0.0",
)


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


# Register authentication endpoints
app.include_router(auth_router)
app.include_router(properties_router)
app.include_router(rental_requests_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to HomeRent API!",
        "status": "running",
    }


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception:
        return {
            "status": "unhealthy",
            "database": "disconnected",
        }
