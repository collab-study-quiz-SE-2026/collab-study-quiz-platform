from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class QuestionCreate(BaseModel):
    question_text: str = Field(min_length=1)
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer_index: int = Field(ge=0)
    topic: str = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"]

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
