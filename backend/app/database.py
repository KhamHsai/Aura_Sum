from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Create engine with pool_pre_ping=True for MySQL reliability
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Session factory for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base class for models
Base = declarative_base()

# FastAPI database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
