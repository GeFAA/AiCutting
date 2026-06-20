from aicutting.core.models import ClipCandidate


def rank_candidates(candidates: list[ClipCandidate]) -> list[ClipCandidate]:
    ranked = sorted(candidates, key=lambda candidate: candidate.quality_score, reverse=True)
    output: list[ClipCandidate] = []
    used_keys: set[str] = set()
    deferred: list[ClipCandidate] = []
    for candidate in ranked:
        if candidate.diversity_key in used_keys:
            deferred.append(candidate)
        else:
            output.append(candidate)
            used_keys.add(candidate.diversity_key)
    return output + deferred
