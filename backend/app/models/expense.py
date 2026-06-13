from sqlalchemy import Column, String, DateTime, Date, Time, Text, DECIMAL, Boolean, JSON, ForeignKey, func, Index
from sqlalchemy.dialects.mysql import BIGINT, INTEGER as INT
from sqlalchemy.orm import relationship
from app.database import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id = Column(BIGINT(unsigned=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    category_id = Column(INT(unsigned=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    merchant_name = Column(String(255), nullable=True)
    receipt_number = Column(String(100), nullable=True)
    receipt_date = Column(Date, nullable=False, index=True)
    receipt_time = Column(Time, nullable=True)
    document_type = Column(String(50), nullable=False, default="manual_expense")
    payment_method = Column(String(50), nullable=True)
    currency = Column(String(10), nullable=False, default="THB")
    subtotal = Column(DECIMAL(12, 2), nullable=True)
    tax_amount = Column(DECIMAL(12, 2), nullable=True)
    discount_amount = Column(DECIMAL(12, 2), nullable=True)
    total_amount = Column(DECIMAL(12, 2), nullable=False)
    notes = Column(Text, nullable=True)
    input_method = Column(String(50), nullable=False)
    language_detected = Column(String(20), nullable=True)
    ai_confidence = Column(DECIMAL(5, 4), nullable=True)
    ai_status = Column(String(30), nullable=False, default="not_used")
    ai_raw_response = Column(JSON, nullable=True)
    is_confirmed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")
    # Removing delete-orphan as requested, but keeping standard relationship
    expense_items = relationship("ExpenseItem", back_populates="expense")
    receipt_files = relationship("ReceiptFile", back_populates="expense")

    __table_args__ = (
        Index("idx_expenses_user_receipt_date", "user_id", "receipt_date"),
    )