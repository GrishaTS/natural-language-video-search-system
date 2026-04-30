from __future__ import annotations

from pydantic import BaseModel, Field


class PlateEntry(BaseModel):
    """A license plate value with its event count."""

    number: str = Field(
        description="Номерной знак транспортного средства (lowercase, как вернул VMS)"
    )
    count: int = Field(description="Сколько раз этот номер встретился в событиях")


class LocationEntry(BaseModel):
    """A single location with its event count."""

    address: str = Field(
        description="Полный адрес объекта из channel_address.string_value"
    )
    count: int = Field(
        description="Количество событий, зафиксированных по этому адресу"
    )


class ChannelEntry(BaseModel):
    """A single camera channel with its event count."""

    name: str = Field(description="Имя камеры/канала (channel_name), например '1-3-10'")
    count: int = Field(description="Количество событий с этой камеры")


class TagEntry(BaseModel):
    """A single VMS tag with its event count."""

    name: str = Field(
        description="Имя тега, например 'Floor 3', 'Access control', 'Outdoors'"
    )
    count: int = Field(description="Сколько раз этот тег встречается по всем событиям")


class EventTypeEntry(BaseModel):
    """A VMS event topic with its event count."""

    topic: str = Field(
        description="Тип события VMS: ObjectInside, FaceMatched, PlateNotMatched и др."
    )
    count: int = Field(description="Количество событий данного типа")


class QueryContext(BaseModel):
    """Search context derived from the EventFilter and matched events."""

    domain: str = Field(description="Домен поиска: PEOPLE, VEHICLES или ALL")
    person_name: str | None = Field(
        description="Имя искомой персоны из фильтра (если задано)"
    )
    plate_number: str | None = Field(description="Номер авто из фильтра (если задан)")
    since: str | None = Field(
        description="Начало временного диапазона поиска (ISO 8601 UTC)"
    )
    until: str | None = Field(
        description="Конец временного диапазона поиска (ISO 8601 UTC)"
    )
    channels_searched: int = Field(
        description="Количество камер, по которым выполнялся поиск"
    )
    channel_names: list[str] = Field(
        description="Названия камер, разрешённые из событий (может быть неполным, если событий мало)"
    )
    tags_searched: int = Field(description="Количество тегов (зон/этажей) в фильтре")
    tag_names: list[str] = Field(description="Названия тегов, разрешённые из событий")


class MetricsBase(BaseModel):
    """Base event metrics shared by all summary types."""

    events_count: int = Field(description="Всего событий возвращено поиском")
    first_seen: str | None = Field(description="Время первого события (ISO 8601 UTC)")
    last_seen: str | None = Field(description="Время последнего события (ISO 8601 UTC)")
    unique_days: int = Field(
        description="Количество уникальных дат, в которые зафиксированы события"
    )


class LocationStats(BaseModel):
    """Aggregated location statistics for an event set."""

    top_locations: list[LocationEntry] = Field(
        description="Топ-3 адреса по количеству событий"
    )
    unique_locations: int = Field(description="Количество уникальных адресов")
    first_location: str | None = Field(description="Адрес первого по времени события")
    last_location: str | None = Field(description="Адрес последнего по времени события")


class ChannelStats(BaseModel):
    """Aggregated channel statistics for an event set."""

    top_channels: list[ChannelEntry] = Field(
        description="Топ-3 камеры по количеству событий"
    )
    unique_channels: int = Field(
        description="Количество уникальных камер в результатах"
    )
    channel_types: dict[str, int] = Field(
        description="Распределение по типу канала: {'STREAM': N, ...}"
    )


class TagStats(BaseModel):
    """Aggregated tag statistics for an event set."""

    top_tags: list[TagEntry] = Field(description="Топ-5 тегов по частоте встречаемости")
    unique_tags: int = Field(description="Количество уникальных тегов в результатах")


class PeopleMetrics(MetricsBase):
    """People-domain event metrics."""

    pass


class IdentifiedPersonEntry(BaseModel):
    """A recognized person with count and timing metadata."""

    full_name: str = Field(description="Полное имя человека: 'Имя Фамилия'")
    count: int = Field(description="Количество событий, где этот человек — лучший матч")
    avg_similarity: float = Field(
        description="Средняя уверенность совпадения (0.0–1.0)"
    )
    first_seen: str | None = Field(description="Время первого появления (ISO 8601 UTC)")
    last_seen: str | None = Field(
        description="Время последнего появления (ISO 8601 UTC)"
    )


class WatchlistEntry(BaseModel):
    """A VMS watchlist match count and priority level."""

    list_name: str = Field(description="Название сторожевого списка")
    count: int = Field(description="Количество событий из этого списка")
    level: int = Field(description="Уровень списка (приоритет/угроза)")


class FaceIdentityStats(BaseModel):
    """Aggregated identity and watchlist statistics for face events."""

    identified_count: int = Field(
        description="Количество событий, где хотя бы один человек идентифицирован"
    )
    unidentified_count: int = Field(
        description="Количество событий без совпадений в базе"
    )
    unique_persons: int = Field(
        description="Количество уникальных идентифицированных людей"
    )
    top_persons: list[IdentifiedPersonEntry] = Field(
        description="Топ-5 людей по количеству появлений"
    )
    top_watchlists: list[WatchlistEntry] = Field(
        description="Топ-3 сторожевых списка по частоте срабатывания"
    )
    avg_similarity: float | None = Field(
        description="Средняя уверенность совпадения по всем идентифицированным событиям"
    )


class PeopleAttributes(BaseModel):
    """Aggregated physical attribute distributions for people events."""

    gender_distribution: dict[str, int] = Field(
        description="Распределение по полу: {'male': N, 'female': M}"
    )
    age_avg: float | None = Field(
        description="Средний возраст определённый детектором (None если нет данных)"
    )
    age_min: int | None = Field(description="Минимальный возраст среди событий")
    age_max: int | None = Field(description="Максимальный возраст среди событий")
    beard_distribution: dict[str, int] = Field(
        description="Наличие бороды: {'True': N, 'False': M}"
    )
    glasses_distribution: dict[str, int] = Field(
        description="Наличие очков: {'True': N, 'False': M}"
    )
    hat_distribution: dict[str, int] = Field(
        description="Наличие головного убора: {'True': N, 'False': M}"
    )
    mask_distribution: dict[str, int] = Field(
        description="Наличие маски: {'True': N, 'False': M}"
    )
    race_distribution: dict[str, int] = Field(
        description="Распределение по расе: {'white': N, 'asian': M, ...}"
    )


class PeopleSummary(BaseModel):
    """Full typed summary for people-domain search results."""

    query: QueryContext
    metrics: PeopleMetrics
    attributes: PeopleAttributes
    identities: FaceIdentityStats
    location: LocationStats
    channels: ChannelStats
    tags: TagStats


class VehicleMetrics(MetricsBase):
    """Vehicle-domain event metrics."""

    plate_events: int = Field(
        description="Количество событий, где распознан номерной знак (params.plate присутствует)"
    )


class PlateStats(BaseModel):
    """Aggregated license plate statistics."""

    top_plates: list[PlateEntry] = Field(
        description="Топ номеров по частоте встречаемости"
    )
    unique_plates: int = Field(description="Количество уникальных номерных знаков")
    first_plate: str | None = Field(description="Номер авто из самого раннего события")
    last_plate: str | None = Field(description="Номер авто из самого позднего события")


class VehicleAttributes(BaseModel):
    """Aggregated vehicle brand, color, and type distributions."""

    brand_distribution: dict[str, int] = Field(
        description="Марки ТС по частоте (без 'UNKNOWN'): {'Toyota': N, ...}"
    )
    color_distribution: dict[str, int] = Field(
        description="Цвета ТС по частоте: {'red': N, 'white': M, ...}"
    )
    type_distribution: dict[str, int] = Field(
        description="Типы ТС: {'car': N, 'bus': M, 'truck': K, ...}"
    )


class VehicleSummary(BaseModel):
    """Full typed summary for vehicle-domain search results."""

    query: QueryContext
    metrics: VehicleMetrics
    plates: PlateStats
    attributes: VehicleAttributes
    location: LocationStats
    channels: ChannelStats
    tags: TagStats


class AllMetrics(MetricsBase):
    """Cross-domain event metrics split by event category."""

    face_events: int = Field(
        description="События с распознаванием лица (FaceMatched и подобные)"
    )
    vehicle_events: int = Field(
        description="События с распознаванием номера/ТС (PlateMatched, PlateNotMatched)"
    )
    access_events: int = Field(
        description="События контроля доступа (тег 'Access control')"
    )
    object_events: int = Field(
        description="События отслеживания объектов (module=KX.ObjectTrack, ObjectInside)"
    )
    other_events: int = Field(
        description="Прочие события, не вошедшие в категории выше"
    )


class AllEvents(BaseModel):
    """Aggregated event-topic statistics for all-domain search results."""

    top_event_types: list[EventTypeEntry] = Field(
        description="Топ-5 типов событий (topic) по частоте"
    )
    unique_event_types: int = Field(description="Количество уникальных типов событий")


class AllSummary(BaseModel):
    """Full typed summary for all-domain search results."""

    query: QueryContext
    metrics: AllMetrics
    events: AllEvents
    vehicles: PlateStats = Field(
        description="Статистика по номерам (если есть vehicle events)"
    )
    location: LocationStats
    channels: ChannelStats
    tags: TagStats
