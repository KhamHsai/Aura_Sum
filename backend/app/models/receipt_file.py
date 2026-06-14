from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship
from app.database import Base

class ReceiptFile(Base):
    __tablename__ = "receipt_files"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    expense_id = Column(BIGINT(unsigned=True), ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(BIGINT(unsigned=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), unique=True, nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(BIGINT(unsigned=True), nullable=False)
    file_hash = Column(String(64), nullable=True, index=True)
    upload_status = Column(String(30), nullable=False, default="uploaded")
    uploaded_at = Column(DateTime, nullable=False, server_default=func.now())
    deleted_at = Column(DateTime, nullable=True, index=True)

    # Relationships
    expense = relationship("Expense", back_populates="receipt_files")
    user = relationship("User", back_populates="receipt_files")
