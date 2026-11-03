from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

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


class QuestionCreate(BaseModel):
    question_text: str = Field(min_length=1)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer_index: int = Field(ge=0)
    topic: str = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    explanation: str | None = None

    @field_validator("question_text", "topic", mode="before")
    @classmethod
    def strip_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("question_text", "topic")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("options", mode="before")
    @classmethod
    def strip_options(cls, value: object) -> object:
        if isinstance(value, list):
            return [option.strip() if isinstance(option, str) else option for option in value]
        return value

    @field_validator("options")
    @classmethod
    def reject_blank_options(cls, value: list[str]) -> list[str]:
        if any(not option for option in value):
            raise ValueError("options must not be blank")
        return value

    @model_validator(mode="after")
    def correct_answer_is_an_option(self) -> "QuestionCreate":
        if self.correct_answer_index >= len(self.options):
            raise ValueError("correct_answer_index must refer to an option")
        return self


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_text: str
    options: list[str]
    correct_answer_index: int
    topic: str
    difficulty: str
    explanation: str | None = None
    creator_id: int
    created_at: datetime


class QuestionListResponse(BaseModel):
    total: int
    items: list[QuestionResponse]
