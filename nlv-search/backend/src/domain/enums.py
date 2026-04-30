from enum import Enum


class EntityType(str, Enum):
    """Supported entity types for conversational search resolution."""

    PERSON = "person"
    ADDRESS = "address"
    VEHICLE = "vehicle"
