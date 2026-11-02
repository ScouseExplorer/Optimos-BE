from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AIUsageResponse(BaseModel):
    id: int
    user_id: int
    action: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    credits_charged: int
    request_id: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
