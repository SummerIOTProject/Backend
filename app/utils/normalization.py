def normalize_allergen_codes(codes: list[str] | None) -> list[str]:
    if not codes:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for code in codes:
        item = code.strip().upper()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


def normalize_ingredient_names(items: list[str] | None) -> list[str]:
    if not items:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in items:
        item = raw.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized
