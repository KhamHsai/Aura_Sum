from sqlalchemy import Column, String, DateTime, Text, ForeignKey, func, Index
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import relationship
from app.database import Base

class Translation(Base):
    __tablename__ = "translations"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    expense_item_id = Column(BIGINT(unsigned=True), ForeignKey("expense_items.id", ondelete="SET NULL"), nullable=True, index=True)
    source_text = Column(Text, nullable=False)
    source_language = Column(String(20), nullable=False)
    target_language = Column(String(20), nullable=False)
    translated_text = Column(Text, nullable=False)
    translation_source = Column(String(30), nullable=False, default="gemini")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True, index=True)

    # Relationships
    expense_item = relationship("ExpenseItem", back_populates="translations")

    __table_args__ = (
        Index("idx_translations_source_target_lang", "source_language", "target_language"),
    )
