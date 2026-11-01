from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import UserRole


class RegistrationRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(RegistrationRequest):
    pass


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole


class RegistrationResponse(BaseModel):
    message: str
    user: UserResponse


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class MessageResponse(BaseModel):
    message: str

class QuizCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    duration_minutes: int = Field(gt=0, le=180)
    question_ids: list[int] = Field(min_length=1)
    max_attempts: int = Field(default=1, ge=1, le=10)

    @field_validator("title")
    @classmethod
    def title_cannot_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be blank")
        return value

    @field_validator("question_ids")
    @classmethod
    def question_ids_must_be_valid(cls, ids: list[int]) -> list[int]:
        if any(question_id <= 0 for question_id in ids):
            raise ValueError("Question IDs must be positive")
        if len(ids) != len(set(ids)):
            raise ValueError("Question IDs must be unique")
        return ids
