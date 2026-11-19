from pydantic import BaseModel, Field


class Account(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9_.-]{3,40}$")
    password: str = Field(min_length=12, max_length=128)


class MFARequest(BaseModel):
    challenge: str = Field(max_length=100)
    code: str = Field(pattern=r"^[0-9]{6}$")
