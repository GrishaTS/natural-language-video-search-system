import pytest
from src.services.entities_populator.qdrant_upsert import _is_russian_address


@pytest.mark.parametrize("address,expected", [
    # Russian variants — must be kept
    ("Беларусь, Минск, Первомайский район, Малявщина, улица Платонова, 20Б к1", True),
    ("Беларусь, Минск, Центральный район, проспект Независимости, 12", True),
    ("Беларусь, Минск, Советский район, улица Якуба Коласа, 5", True),
    # Belarusian variants — must be filtered out
    # Contains Cyrillic 'і' (U+0456)
    ("Беларусь, Мінск, Першамайскі раён, вуліца Платонава, 20Б к1", False),
    # Contains 'вуліц' token
    ("Belarus, Minsk, вуліца Платонава, 20Б", False),
    # Contains 'раён' token
    ("Беларусь, Мінск, Першамайскі раён, 20Б", False),
    # Contains 'мінск' (lowercase check)
    ("Мінск, вуліца Леніна", False),
    # Empty string — keep (caller already strips empties, but be safe)
    ("", True),
])
def test_is_russian_address(address: str, expected: bool):
    assert _is_russian_address(address) == expected
