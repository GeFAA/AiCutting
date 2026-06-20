from dataclasses import dataclass
from pathlib import Path

from aicutting.core.errors import AiCuttingError
from aicutting.core.progress import ProgressCallback
from aicutting.pipeline import CutPipeline, PipelineResult


@dataclass(frozen=True)
class JobRequest:
    input_dir: Path
    music_path: Path | None
    output_dir: Path
    dry_run: bool = False


@dataclass(frozen=True)
class JobSuccess:
    result: PipelineResult


@dataclass(frozen=True)
class JobFailure:
    message: str
    error_type: str


JobResult = JobSuccess | JobFailure


def run_cut_job(
    request: JobRequest,
    pipeline_factory: type[CutPipeline] = CutPipeline,
    progress: ProgressCallback | None = None,
) -> JobResult:
    try:
        result = pipeline_factory().cut(
            input_dir=request.input_dir,
            music_path=request.music_path,
            output_dir=request.output_dir,
            dry_run=request.dry_run,
            progress=progress,
        )
    except AiCuttingError as exc:
        return JobFailure(message=str(exc), error_type=type(exc).__name__)
    except Exception as exc:
        return JobFailure(message=str(exc), error_type=type(exc).__name__)
    return JobSuccess(result=result)
