from pydantic import BaseModel
from src.domain.enums import EntityType


class ResolvedEntity(BaseModel):
    """An entity resolved through Qdrant during the entity resolution step.

    Contains the Qdrant ID, entity type, and display value. Person-specific fields are None for addresses and vehicles.
    """

    entity_type: EntityType
    entity_id: str
    value: str

    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
