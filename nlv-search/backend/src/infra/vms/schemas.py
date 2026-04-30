from enum import Enum
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field, TypeAdapter
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


class PersonFullName(TypedDict):
    """VMS person record with optional name components."""

    id: int
    last_name: str | None
    first_name: str | None
    middle_name: str | None


class VehicleInfo(TypedDict):
    """VMS vehicle record with plate number."""

    id: int
    number: str | None


class LocationInfo(TypedDict):
    """VMS location record with address string."""

    id: int
    address: str | None


class Domain(str, Enum):
    """Supported VMS event search domains."""

    PEOPLE = "PEOPLE"
    VEHICLE = "VEHICLES"
    ALL = "ALL"


class ChannelFilter(BaseModel):
    """Restrict event search to specific camera channels."""

    ids: list[int] | None = Field(default=None, description="IDs видеоканалов (камер).")


class TagFilter(BaseModel):
    """Restrict event search to events carrying specific tags."""

    ids: list[int] | None = Field(
        default=None, description="IDs тегов для фильтрации по этажам."
    )


class AgeParams(BaseModel):
    """Lower and upper bounds for age-based face filtering."""

    lower_bound: int | None = Field(
        default=None, description="Нижняя граница возраста человека."
    )
    upper_bound: int | None = Field(
        default=None, description="Верхняя граница возраста человека."
    )


class FaceAttributes(BaseModel):
    """Physical attribute filters for face-based event search."""

    age: list[AgeParams] | None = Field(
        default=None, description="Диапазоны возраста людей для поиска."
    )
    genders: list[Gender] | None = Field(
        default=None, description="Фильтр по полу человека."
    )
    beard: list[Beard] | None = Field(
        default=None, description="Наличие или отсутствие бороды."
    )
    glasses: list[Glasses] | None = Field(
        default=None, description="Наличие или отсутствие очков."
    )
    races: list[Race] | None = Field(
        default=None, description="Раса человека, определённая системой распознавания."
    )
    hat: list[Hat] | None = Field(
        default=None, description="Наличие или отсутствие головного убора."
    )
    mask: list[Mask] | None = Field(
        default=None, description="Наличие или отсутствие маски на лице."
    )


class FaceDescriptorVersion(BaseModel):
    """Version metadata for a face descriptor vector."""

    alg_type: int
    major_version: int
    minor_version: int


class FaceDescriptorItem(BaseModel):
    """A single face descriptor with its algorithm version."""

    descriptor: str
    version: FaceDescriptorVersion


class FaceMatchFilter(BaseModel):
    """Face search by descriptor similarity."""

    type: Literal["BY_DESC"] = "BY_DESC"
    descriptors: list[list[FaceDescriptorItem]]
    min_similarity: float = 0.7


class FaceFilter(BaseModel):
    """Face filter combining known face IDs and/or attribute constraints."""

    face_ids: list[int] | None = Field(
        default=None,
        description="IDs записей из реестра face-manager для поиска по конкретным персонам.",
    )
    attributes: FaceAttributes | None = Field(
        default=None,
        description="Набор атрибутов лица, используемых для поиска человека.",
    )


class PlateFilter(BaseModel):
    """Vehicle plate number filter."""

    number: str | None = Field(
        default=None, description="Номер транспортного средства для поиска."
    )


class PersonFilter(BaseModel):
    """Person name filter for VMS people search."""

    first_name: str | None = Field(default=None, description="Имя человека для поиска.")
    last_name: str | None = Field(
        default=None, description="Фамилия человека для поиска."
    )
    middle_name: str | None = Field(
        default=None, description="Отчество человека для поиска."
    )


class BaseEventFilter(BaseModel):
    """Common VMS event-search fields shared by all domains."""

    event_search_request_source: str = Field(
        default="SEARCH_PAGE", description="Источник запроса поиска событий."
    )
    channel: ChannelFilter | None = Field(
        default=None, description="Фильтр по видеоканалам (камерам)."
    )
    tag: TagFilter | None = Field(default=None, description="Фильтр по тегам событий.")
    since: str | None = Field(
        default=None,
        description="Начало временного диапазона поиска (timestamp: ISO 8601 UTC format (YYYY-MM-DDTHH:MM:SSZ)).",
    )
    until: str | None = Field(
        default=None,
        description="Конец временного диапазона поиска (timestamp: ISO 8601 UTC format (YYYY-MM-DDTHH:MM:SSZ)).",
    )


class PersonEventFilter(BaseEventFilter):
    """VMS event filter for the PEOPLE domain."""

    domain: Literal[Domain.PEOPLE] = Field(
        default=Domain.PEOPLE,
        description="Тип запроса направленный на поиска событий с участием людей.",
    )
    topics_by_modules: dict | None = Field(
        default={
            "KX.Faces": ["FaceMatched", "FaceNotMatched"],
            "KX.Hikvision": ["Temperature", "FaceMatched", "FaceNotMatched"],
        },
        description="Фильтр по модулям и топикам событий.",
    )
    face: FaceFilter | None = Field(
        default=None, description="Фильтр по face_ids и/или атрибутам лица."
    )
    face_match: FaceMatchFilter | None = Field(
        default=None,
        description="Поиск по дескриптору лица (BY_DESC). Взаимоисключает face.face_ids.",
    )


class VehicleEventFilter(BaseEventFilter):
    """VMS event filter for the VEHICLE domain."""

    domain: Literal[Domain.VEHICLE] = Field(
        default=Domain.VEHICLE,
        description="Тип запроса направленный на поиска событий с участием транспортных средств.",
    )
    person: PersonFilter | None = Field(
        default=None, description="Фильтр по владельцу или связанному человеку."
    )
    plate: PlateFilter | None = Field(
        default=None, description="Фильтр по номерному знаку транспортного средства."
    )
    car_brands: list[CarBrand] | None = Field(
        default=None, description="Марки автомобилей для поиска."
    )
    colors: list[VehicleColor] | None = Field(
        default=None, description="Цвета транспортных средств."
    )
    object_types: list[ObjectType] | None = Field(
        default=None, description="Типы транспортных средств."
    )


class AllEventFilter(BaseEventFilter):
    """VMS event filter with no domain restriction."""

    domain: Literal[Domain.ALL] = Field(
        default=Domain.ALL,
        description="Тип запроса направленный на поиска событий без указания сущностей и их описаний.",
    )


EventFilter = Annotated[
    PersonEventFilter | VehicleEventFilter | AllEventFilter,
    Field(discriminator="domain"),
]
