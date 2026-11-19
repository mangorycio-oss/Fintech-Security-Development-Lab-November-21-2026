from pydantic import BaseModel, Field


class PaymentRequest(BaseModel):
    amount_krw: int = Field(ge=1, le=10_000_000)
