
from sqlalchemy import text
from database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))
        print("PostgreSQL connected successfully!")
        print(result.scalar())
except Exception as error:
    print("Database connection failed:")
    print(error)
