def choose_target_duration(total_usable_s: float) -> float:
    # Match the song so the whole track plays and the cut showcases more of the footage, rather than
    # a fixed highlight length. Clamp so a tiny clip still makes a short cut and an unusually long
    # track stays a sane length (and render).
    return round(min(max(total_usable_s, 15.0), 300.0), 3)
