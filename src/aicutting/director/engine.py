from dataclasses import dataclass

from aicutting.core.models import AnalysisReport, ClipCandidate
from aicutting.director.models import DirectorDecision, DirectorReport, RejectedSegment


@dataclass(frozen=True)
class DirectorOutputs:
    analysis: AnalysisReport
    director_report: DirectorReport
    rejected_segments: list[RejectedSegment]


def build_director_outputs(report: AnalysisReport) -> DirectorOutputs:
    accepted: list[ClipCandidate] = []
    rejected: list[RejectedSegment] = []
    decisions: list[DirectorDecision] = []
    for candidate in report.candidates:
        score = candidate.director_score
        if candidate.rejection_reason:
            rejected.append(
                RejectedSegment(
                    asset_path=candidate.asset_path,
                    start_s=candidate.start_s,
                    end_s=candidate.end_s,
                    reason=candidate.rejection_reason,
                    score=score,
                )
            )
            decisions.append(
                DirectorDecision(
                    asset_path=candidate.asset_path,
                    start_s=candidate.start_s,
                    end_s=candidate.end_s,
                    selected=False,
                    reason=candidate.rejection_reason,
                    score=score,
                )
            )
        else:
            accepted.append(candidate)
            decisions.append(
                DirectorDecision(
                    asset_path=candidate.asset_path,
                    start_s=candidate.start_s,
                    end_s=candidate.end_s,
                    selected=True,
                    reason=f"{candidate.movement_type} usability {score:.2f}",
                    score=score,
                )
            )
    # Lead the report with the clips the director chose (highest score first),
    # then the rejections; iteration order alone would bury selections behind cuts.
    decisions.sort(key=lambda decision: (decision.selected, decision.score), reverse=True)
    filtered = report.model_copy(update={"candidates": accepted or report.candidates})
    warnings = [] if accepted else ["All candidates were rejected; using fallback candidates."]
    return DirectorOutputs(
        analysis=filtered,
        director_report=DirectorReport(decisions=decisions, warnings=warnings),
        rejected_segments=rejected,
    )
