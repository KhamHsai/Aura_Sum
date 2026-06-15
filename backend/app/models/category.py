from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.mysql import INTEGER as INT
from sqlalchemy.orm import relationship
from app.database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(INT(unsigned=True), primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name_en = Column(String(100), unique=True, nullable=False, index=True)
    name_th = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True, index=True)

    # Relationships
    expenses = relationship("Expense", back_populates="category")
    expense_items = relationship("ExpenseItem", back_populates="category")