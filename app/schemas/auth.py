from pydantic import BaseModel, EmailStr, Field
from datetime import date


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    name: str | None = None
    surname: str | None = None
    birthdate: date | None = None  # ISO format date string
    country: str | None = None


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    userid: int
    username: str
    email: EmailStr

    class Config:
        from_attributes = True


class AuthUserResponse(BaseModel):
    user: UserOut


class MessageResponse(BaseModel):
    detail: str
