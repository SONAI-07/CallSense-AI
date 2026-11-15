from datetime import datetime

from pydantic import BaseModel, ConfigDict , Field


class CustomerResponse(BaseModel):
    id: int
    name: str
    phone_number: str
    email: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CustomerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone_number: str = Field(min_length=8, max_length=20)
    email: EmailStr | None = None