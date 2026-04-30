from typing import Annotated, Literal

from pydantic import BaseModel, Field
from src.domain.attributes import (
    Beard,
    CarBrand,
    Gender,
    Glasses,
    Hat,
    Mask,
    ObjectType,
    Race,
    VehicleColor,
)


class TimeRange(BaseModel):
    """Absolute time window for event queries."""

    since: str = Field(description="ISO 8601 UTC. Пример: '2025-01-01T00:00:00Z'")
    until: str = Field(description="ISO 8601 UTC. Пример: '2025-01-31T23:59:59Z'")


class PersonQuery(BaseModel):
    """Person name query extracted from user text."""

    name: str = Field(
        description="ФИО или часть имени для поиска в Qdrant. "
        "Нормализованная форма без уточнений. "
        "Примеры: 'Петров', 'Иван Петров', 'Герман Петров'"
    )
    query_text: str = Field(
        description="Как именно написано в запросе пользователя — "
        "нужно для entity resolution. "
        "Примеры: 'все Петровы', 'Г. Петров', 'Герман'"
    )


class AddressQuery(BaseModel):
    """Address query extracted from user text."""

    value: str = Field(
        description="Адрес для поиска в Qdrant без уточнений корпуса/всех корпусов. "
        "Пример: 'Платонова 20б'"
    )
    query_text: str = Field(
        description="Полное описание из запроса пользователя с уточнениями. "
        "Нужно для entity resolution. "
        "Примеры: 'Платонова 20б все корпуса', 'Платонова 20б к1-3'"
    )


class VehiclePlateQuery(BaseModel):
    """Vehicle plate query extracted from user text."""

    plate: str = Field(
        description="Номерной знак транспортного средства для поиска в Qdrant. "
        "Пример: 'АА123ББ'"
    )
    query_text: str = Field(
        description="Как написано в запросе пользователя. "
        "Пример: 'синяя Газель АА123ББ'"
    )


class AgeRangeQuery(BaseModel):
    """Age range filter extracted from user text."""

    lower_bound: int | None = None
    upper_bound: int | None = None


class FaceAttributesQuery(BaseModel):
    """Face attribute filters extracted from user text."""

    age: list[AgeRangeQuery] | None = None
    genders: list[Gender] | None = None
    beard: list[Beard] | None = None
    glasses: list[Glasses] | None = None
    races: list[Race] | None = Field(
        default=None,
        description="white / black / asian / indian / other / middle_eastern / latino",
    )
    hat: list[Hat] | None = None
    mask: list[Mask] | None = None


class PeopleQuerySchema(BaseModel):
    """Parsed PEOPLE-domain conversational search query."""

    domain: Literal["PEOPLE"]
    persons: list[PersonQuery] = Field(
        default_factory=list,
        description="Люди для поиска. Пустой список = поиск без конкретного человека",
    )
    addresses: list[AddressQuery] = Field(
        default_factory=list,
        description="Адреса для фильтрации камер",
    )
    floors: list[int] = Field(
        default_factory=list,
        description="Этажи для фильтрации по тегам",
    )
    time_range: TimeRange | None = Field(default=None)
    face_attributes: FaceAttributesQuery | None = Field(
        default=None,
        description="Атрибуты внешности: возраст, пол, борода, очки, раса, шапка, маска",
    )
    is_refinement: bool = Field(
        description="True = уточнение предыдущего запроса. "
        "Незаполненные поля берутся из предыдущего состояния"
    )


class VehiclesQuerySchema(BaseModel):
    """Parsed VEHICLES-domain conversational search query."""

    domain: Literal["VEHICLES"]
    plates: list[VehiclePlateQuery] = Field(
        default_factory=list,
        description="Конкретные ТС по номеру. Пустой список = поиск по атрибутам без конкретного ТС",
    )
    addresses: list[AddressQuery] = Field(default_factory=list)
    floors: list[int] = Field(default_factory=list)
    time_range: TimeRange | None = Field(default=None)
    car_brands: list[CarBrand] | None = Field(
        default=None,
        description="Марки: AUDI, BMW, MERCEDES_BENZ, TOYOTA, LADA и др.",
    )
    colors: list[VehicleColor] | None = Field(
        default=None,
        description="Цвета: white / yellow / orange / red / green / blue / brown / gray / black",
    )
    object_types: list[ObjectType] | None = Field(
        default=None,
        description="Типы ТС: bus / car / truck / van",
    )
    is_refinement: bool = Field(description="True = уточнение предыдущего запроса")


class AllQuerySchema(BaseModel):
    """Parsed all-domain conversational search query."""

    domain: Literal["ALL"]
    addresses: list[AddressQuery] = Field(default_factory=list)
    floors: list[int] = Field(default_factory=list)
    time_range: TimeRange | None = Field(default=None)
    is_refinement: bool = Field(description="True = уточнение предыдущего запроса")


QuerySchema = Annotated[
    PeopleQuerySchema | VehiclesQuerySchema | AllQuerySchema,
    Field(discriminator="domain"),
]


class ParsedQuery(BaseModel):
    """Wrapper around the discriminated query union for structured LLM output."""

    query: Annotated[
        PeopleQuerySchema | VehiclesQuerySchema | AllQuerySchema,
        Field(discriminator="domain"),
    ]
