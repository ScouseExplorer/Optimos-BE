from typing import Literal

from pydantic import BaseModel, Field


class PurchaseIntentRequest(BaseModel):
    credits: int = Field(ge=1, le=1_000_000)
    success_url: str
    cancel_url: str


class PurchaseIntentResponse(BaseModel):
    checkout_url: str
    provider_intent_id: str


class SubscriptionIntentRequest(BaseModel):
    tier: Literal["pro", "enterprise"]


class CustomerPortalResponse(BaseModel):
    portal_url: str
