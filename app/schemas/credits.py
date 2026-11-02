from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreditWalletResponse(BaseModel):
    id: int
    user_id: int
    balance: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreditTransactionResponse(BaseModel):
    id: int
    user_id: int
    amount: int
    transaction_type: str
    source: str
    reference_id: str | None = None
    request_id: str | None = None
    status: str
    description: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeatureCostResponse(BaseModel):
    id: int
    feature_key: str
    credit_cost: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AdminCreditAdjustmentRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    amount: int
    description: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_non_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("amount must not be zero")
        return value
