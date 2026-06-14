from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ReceiptFileResponse(BaseModel):
    """Safe receipt file fields returned to the client."""
    id: int
    user_id: int
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: int
    upload_status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
