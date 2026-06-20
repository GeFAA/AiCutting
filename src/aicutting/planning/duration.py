def choose_target_duration(total_usable_s: float) -> float:
    if total_usable_s <= 45.0:
        return round(max(15.0, total_usable_s), 3)
    if total_usable_s <= 240.0:
        return 75.0
    return 180.0
