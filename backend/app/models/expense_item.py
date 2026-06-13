from sqlalchemy import Column, String, DateTime, DECIMAL, ForeignKey, func
from sqlalchemy.dialects.mysql import BIGINT, INTEGER as INT
from sqlalchemy.orm import relationship
from app.database import Base

class ExpenseItem(Base):
    __tablename__ = "expense_items"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    expense_id = Column(BIGINT(unsigned=True), ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(INT(unsigned=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    original_name = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=True)
    name_th = Column(String(255), nullable=True)
    quantity = Column(DECIMAL(10, 3), nullable=False, default=1.000)
    unit = Column(String(30), nullable=True)
    unit_price = Column(DECIMAL(12, 2), nullable=True)
    discount_amount = Column(DECIMAL(12, 2), nullable=False, default=0.00)
    total_price = Column(DECIMAL(12, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True, index=True)

    # Relationships
    expense = relationship("Expense", back_populates="expense_items")
    category = relationship("Category", back_populates="expense_items")
    # Removing delete-orphan as requested
    translations = relationship("Translation", back_populates="expense_item")