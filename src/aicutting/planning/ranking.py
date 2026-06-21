from aicutting.core.models import ClipCandidate


def rank_candidates(candidates: list[ClipCandidate]) -> list[ClipCandidate]:
    ranked = sorted(candidates, key=lambda candidate: candidate.composite_score, reverse=True)
    diversified: list[ClipCandidate] = []
    used_keys: set[str] = set()
    deferred: list[ClipCandidate] = []
    for candidate in ranked:
        if candidate.diversity_key in used_keys:
            deferred.append(candidate)
        else:
            diversified.append(candidate)
            used_keys.add(candidate.diversity_key)
    return _interleave_source_assets(diversified + deferred)


def _interleave_source_assets(candidates: list[ClipCandidate]) -> list[ClipCandidate]:
    grouped: dict[str, list[ClipCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.asset_path.as_posix(), []).append(candidate)

    output: list[ClipCandidate] = []
    previous_asset: str | None = None
    while grouped:
        selectable = [
            (asset, items[0])
            for asset, items in grouped.items()
            if asset != previous_asset or len(grouped) == 1
        ]
        selected_asset, selected_candidate = max(
            selectable,
            key=lambda item: item[1].composite_score,
        )
        output.append(selected_candidate)
        previous_asset = selected_asset
        grouped[selected_asset].pop(0)
        if not grouped[selected_asset]:
            del grouped[selected_asset]
    return output
