def person_alias_variants(first: str, middle: str, last: str) -> list[str]:
    """Generate name alias variants for a person.

    Args:
        first: Given name.
        middle: Patronymic.
        last: Family name.

    Returns:
        List of alias strings to index in the aliases Qdrant collection.
    """

    variants = {
        " ".join(filter(None, [first, middle, last])).strip(),
        " ".join(filter(None, [last, first, middle])).strip(),
        " ".join(filter(None, [last, first])).strip(),
        " ".join(filter(None, [first, last])).strip(),
    }
    return [v for v in variants if v]
