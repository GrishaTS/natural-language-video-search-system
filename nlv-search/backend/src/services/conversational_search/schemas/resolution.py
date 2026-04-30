from typing import Annotated, Literal

from pydantic import BaseModel, Field


class AutoResolve(BaseModel):
    """Entity resolution decision selected automatically by the LLM."""

    type: Literal["auto_resolve"]
    selected_ids: list[str] = Field(
        min_length=1,
        max_length=10,
        description=(
            "Позиционные ключи выбранных кандидатов (p0, p1, a0, v0 и т.д.). "
            "Только ключи из списка выше. Каждый ключ — не более одного раза. Не менее 1, не более 10."
        ),
    )


class UserResolve(BaseModel):
    """Entity resolution decision that requires user selection."""

    type: Literal["user_resolve"]
    filtered_options: list[str] = Field(
        min_length=2,
        max_length=10,
        description=(
            "Позиционные ключи кандидатов для показа пользователю (p0, p1, a0, v0 и т.д.). "
            "Только ключи из списка выше. Каждый ключ — не более одного раза. "
            "Включать только реально подходящих. Не менее 2, не более 10."
        ),
    )


class EntityDecision(BaseModel):
    """Resolution decision for a single entity mention from the user query."""

    entity_value: str = Field(
        description="query_text сущности из запроса пользователя (для отображения юзеру)",
    )
    decision: Annotated[AutoResolve | UserResolve, Field(discriminator="type")] = Field(
        description=(
            "auto_resolve — LLM уверен в выборе, выбирает сам; "
            "user_resolve — несколько равнозначных вариантов, нужен выбор пользователя"
        ),
    )


class ResolutionOutput(BaseModel):
    """Structured output containing all entity resolution decisions."""

    decisions: list[EntityDecision] = Field(
        description="По одному решению на каждую сущность из запроса. Пустой список если сущностей нет.",
    )
