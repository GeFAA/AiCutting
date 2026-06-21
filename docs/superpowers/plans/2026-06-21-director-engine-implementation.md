# AiCutting Director Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first professional Director Engine layer that rejects poor drone motion, plans beat-aware cuts, explains decisions, and gates location/title overlays by confidence.

**Architecture:** Keep `CutPipeline` as the CLI/GUI entry point. Add focused director modules for motion scoring, decision reports, location suggestions, and title overlays, then integrate them into analysis, planning, rendering, and artifact writing. Preserve the current FFmpeg renderer while extending it with fast clip seeking, correct transition timing, and optional title metadata.

**Tech Stack:** Python 3.11+, OpenCV, NumPy, Pydantic, FFmpeg/ffprobe, pytest, ruff, mypy, optional Codex/Claude local command backends.

---

## File Structure

- Modify `src/aicutting/core/models.py`: extend candidate and timeline models with motion/director/title metadata while keeping JSON compatibility.
- Modify `src/aicutting/analysis/video.py`: keep window generation and frame quality scoring, integrate motion scoring.
- Create `src/aicutting/analysis/motion.py`: optical-flow, jitter, direction stability, movement type, and rejection decisions.
- Create `src/aicutting/analysis/screenshots.py`: deterministic keyframe extraction and optional contact-sheet support.
- Create `src/aicutting/director/__init__.py`: package marker.
- Create `src/aicutting/director/models.py`: `DirectorDecision`, `DirectorReport`, `RejectedSegment`, and `LocationSuggestion`.
- Create `src/aicutting/director/location.py`: metadata-first and agent-assisted location-title suggestions with confidence gating.
- Create `src/aicutting/director/engine.py`: director orchestration for accepted/rejected candidates, beat timing, transition validation, and report creation.
- Modify `src/aicutting/planning/engine.py`: use director-aware candidate scores and timing helpers.
- Modify `src/aicutting/planning/ranking.py`: preserve source diversity while using usability when present.
- Modify `src/aicutting/render/ffmpeg.py`: retain fast `-ss`/`-t` input seeking, correct mixed hard-cut/dissolve rendering, and optional title overlay injection.
- Create `src/aicutting/render/titles.py`: FFmpeg drawtext title overlay construction and font discovery.
- Modify `src/aicutting/pipeline.py`: write `director-report.json`, `rejected-segments.json`, and `location-suggestions.json`.
- Add tests under `tests/analysis`, `tests/director`, `tests/render`, and update pipeline/planning tests.

## Task 1: Commit Existing Foundation Fixes

**Files:**
- Modify: existing dirty changes in `src/aicutting/analysis/video.py`
- Modify: existing dirty changes in `src/aicutting/pipeline.py`
- Modify: existing dirty changes in `src/aicutting/planning/engine.py`
- Modify: existing dirty changes in `src/aicutting/planning/ranking.py`
- Modify: existing dirty changes in `src/aicutting/render/ffmpeg.py`
- Modify: existing dirty changes in related tests

- [ ] **Step 1: Verify foundation behavior**

Run:

```powershell
py -m pytest -q
py -m ruff check .
py -m mypy src
```

Expected:

```text
85 passed
All checks passed!
Success: no issues found in 36 source files
```

- [ ] **Step 2: Inspect the foundation diff**

Run:

```powershell
git diff --stat
git diff -- src/aicutting/analysis/video.py src/aicutting/planning/engine.py src/aicutting/render/ffmpeg.py
```

Expected: diff is limited to real candidate windows, beat-aware duration selection, source interleaving, and fast FFmpeg seeking/transition rendering.

- [ ] **Step 3: Commit foundation changes**

Run:

```powershell
git add src/aicutting/analysis/video.py src/aicutting/pipeline.py src/aicutting/planning/engine.py src/aicutting/planning/ranking.py src/aicutting/render/ffmpeg.py tests/analysis/test_video.py tests/planning/test_engine.py tests/planning/test_ranking.py tests/render/test_ffmpeg.py tests/test_pipeline.py
git commit -m "fix: improve automatic cut selection"
```

Expected: commit includes only the existing foundation fixes, not the new Director Engine implementation.

## Task 2: Add Director Models

**Files:**
- Modify: `src/aicutting/core/models.py`
- Create: `src/aicutting/director/__init__.py`
- Create: `src/aicutting/director/models.py`
- Test: `tests/director/test_models.py`

- [ ] **Step 1: Write failing tests**

Create `tests/director/test_models.py`:

```python
from pathlib import Path

from aicutting.core.models import ClipCandidate, LocationTitle
from aicutting.director.models import DirectorDecision, DirectorReport, LocationSuggestion


def test_clip_candidate_accepts_motion_scores_and_rejection_reason() -> None:
    candidate = ClipCandidate(
        asset_path=Path("clip.mp4"),
        start_s=12.0,
        end_s=17.0,
        quality_score=0.8,
        motion_score=0.7,
        diversity_key="clip:1",
        smoothness_score=0.9,
        jitter_score=0.05,
        movement_score=0.85,
        composition_score=0.75,
        usability_score=0.88,
        movement_type="push_in",
        rejection_reason=None,
    )

    assert candidate.usability_score == 0.88
    assert candidate.movement_type == "push_in"
    assert candidate.director_score > candidate.composite_score


def test_director_report_serializes_selected_and_rejected_segments() -> None:
    decision = DirectorDecision(
        asset_path=Path("clip.mp4"),
        start_s=12.0,
        end_s=17.0,
        selected=True,
        reason="smooth push-in near beat",
        score=0.91,
    )
    report = DirectorReport(
        decisions=[decision],
        warnings=[],
        title=LocationTitle(title="Madeira Coast", subtitle="Portugal", confidence=0.86),
    )

    payload = report.model_dump(mode="json")

    assert payload["decisions"][0]["selected"] is True
    assert payload["title"]["title"] == "Madeira Coast"


def test_location_suggestion_requires_confidence_gate() -> None:
    suggestion = LocationSuggestion(
        title="Unknown beach",
        place="unknown",
        confidence=0.42,
        evidence=["agent saw coastline"],
        should_render=True,
    )

    assert suggestion.renderable is False
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
py -m pytest tests/director/test_models.py -q
```

Expected: FAIL because `LocationTitle`, director models, and director fields do not exist.

- [ ] **Step 3: Implement models**

In `src/aicutting/core/models.py`, add `LocationTitle` and extend `ClipCandidate`:

```python
class LocationTitle(BaseModel):
    title: str
    subtitle: str | None = None
    confidence: float = Field(ge=0, le=1)


class ClipCandidate(BaseModel):
    asset_path: Path
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    quality_score: float = Field(ge=0, le=1)
    motion_score: float = Field(ge=0, le=1)
    diversity_key: str
    smoothness_score: float | None = Field(default=None, ge=0, le=1)
    jitter_score: float | None = Field(default=None, ge=0, le=1)
    movement_score: float | None = Field(default=None, ge=0, le=1)
    composition_score: float | None = Field(default=None, ge=0, le=1)
    usability_score: float | None = Field(default=None, ge=0, le=1)
    movement_type: str = "unknown"
    rejection_reason: str | None = None
```

Add:

```python
    @property
    def director_score(self) -> float:
        usability = self.usability_score if self.usability_score is not None else self.composite_score
        return round((self.composite_score * 0.35) + (usability * 0.65), 6)
```

Create `src/aicutting/director/models.py`:

```python
from pathlib import Path

from pydantic import BaseModel, Field

from aicutting.core.models import LocationTitle


class DirectorDecision(BaseModel):
    asset_path: Path
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    selected: bool
    reason: str
    score: float = Field(ge=0, le=1)


class RejectedSegment(BaseModel):
    asset_path: Path
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    reason: str
    score: float = Field(ge=0, le=1)


class LocationSuggestion(BaseModel):
    title: str
    place: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]
    should_render: bool

    @property
    def renderable(self) -> bool:
        return self.should_render and self.confidence >= 0.75


class DirectorReport(BaseModel):
    decisions: list[DirectorDecision]
    warnings: list[str]
    title: LocationTitle | None = None
```

Create `src/aicutting/director/__init__.py` with an empty file.

- [ ] **Step 4: Run tests**

Run:

```powershell
py -m pytest tests/director/test_models.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/aicutting/core/models.py src/aicutting/director/__init__.py src/aicutting/director/models.py tests/director/test_models.py
git commit -m "feat: add director decision models"
```

## Task 3: Implement Motion Analyzer

**Files:**
- Create: `src/aicutting/analysis/motion.py`
- Modify: `src/aicutting/analysis/video.py`
- Test: `tests/analysis/test_motion.py`

- [ ] **Step 1: Write failing tests**

Create `tests/analysis/test_motion.py`:

```python
import numpy as np

from aicutting.analysis.motion import analyze_motion_frames, reject_bad_motion


def _frame(x_offset: int = 0, y_offset: int = 0) -> np.ndarray:
    frame = np.zeros((80, 120, 3), dtype=np.uint8)
    frame[25 + y_offset : 55 + y_offset, 35 + x_offset : 85 + x_offset] = 255
    return frame


def test_smooth_motion_scores_better_than_jittery_motion() -> None:
    smooth = [_frame(index * 2, 0) for index in range(5)]
    jittery = [_frame(offset, 0) for offset in [0, 8, -5, 11, -3]]

    smooth_result = analyze_motion_frames(smooth)
    jitter_result = analyze_motion_frames(jittery)

    assert smooth_result.smoothness_score > jitter_result.smoothness_score
    assert jitter_result.jitter_score > smooth_result.jitter_score


def test_abrupt_direction_change_is_rejected_as_unstable_yaw() -> None:
    frames = [_frame(offset, 0) for offset in [0, 12, 24, 6, -8]]

    result = analyze_motion_frames(frames)
    rejection = reject_bad_motion(result, starts_near_clip_edge=False)

    assert rejection == "unstable_yaw_or_pan"


def test_edge_shaky_motion_is_rejected_as_takeoff_or_landing() -> None:
    frames = [_frame(offset, offset // 2) for offset in [0, 18, -12, 22, -8]]

    result = analyze_motion_frames(frames)
    rejection = reject_bad_motion(result, starts_near_clip_edge=True)

    assert rejection == "takeoff_or_landing_motion"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
py -m pytest tests/analysis/test_motion.py -q
```

Expected: FAIL because `aicutting.analysis.motion` does not exist.

- [ ] **Step 3: Implement motion analysis**

Create `src/aicutting/analysis/motion.py`:

```python
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class MotionAnalysis:
    smoothness_score: float
    jitter_score: float
    movement_score: float
    composition_score: float
    usability_score: float
    movement_type: str


def analyze_motion_frames(frames: list[np.ndarray]) -> MotionAnalysis:
    if len(frames) < 2:
        return MotionAnalysis(0.4, 0.2, 0.2, 0.5, 0.45, "unknown")

    centers = [_bright_center(frame) for frame in frames]
    vectors = [
        (current[0] - previous[0], current[1] - previous[1])
        for previous, current in zip(centers, centers[1:], strict=False)
    ]
    magnitudes = np.array([float(np.hypot(dx, dy)) for dx, dy in vectors], dtype=float)
    if magnitudes.size == 0:
        return MotionAnalysis(0.4, 0.2, 0.2, 0.5, 0.45, "unknown")

    mean_motion = float(np.mean(magnitudes))
    motion_variance = float(np.std(magnitudes))
    direction_changes = _direction_change_ratio(vectors)
    jitter = min(1.0, (motion_variance / 12.0) + (direction_changes * 0.7))
    movement = min(1.0, mean_motion / 18.0)
    smoothness = max(0.0, 1.0 - jitter)
    composition = _composition_stability(centers, frames[0].shape)
    usability = round((smoothness * 0.45) + (movement * 0.25) + (composition * 0.3), 6)
    movement_type = _movement_type(vectors, jitter, movement)
    return MotionAnalysis(
        smoothness_score=round(smoothness, 6),
        jitter_score=round(jitter, 6),
        movement_score=round(movement, 6),
        composition_score=round(composition, 6),
        usability_score=usability,
        movement_type=movement_type,
    )


def reject_bad_motion(result: MotionAnalysis, starts_near_clip_edge: bool) -> str | None:
    if starts_near_clip_edge and result.jitter_score >= 0.55:
        return "takeoff_or_landing_motion"
    if result.jitter_score >= 0.65:
        return "unstable_yaw_or_pan"
    if result.smoothness_score < 0.3:
        return "excessive_jitter"
    if result.movement_type == "searching":
        return "search_flight_before_subject"
    return None
```

Implement private helpers `_bright_center`, `_direction_change_ratio`, `_composition_stability`, and `_movement_type` so the tests pass. Use image moments or bright-pixel averages for synthetic frame stability and fallback to frame center when no bright region exists.

- [ ] **Step 4: Integrate with candidate scoring**

Modify `score_candidates_from_video` in `src/aicutting/analysis/video.py`:

```python
from aicutting.analysis.motion import analyze_motion_frames, reject_bad_motion
```

After reading frames and quality:

```python
motion_result = analyze_motion_frames(frames)
rejection = reject_bad_motion(
    motion_result,
    starts_near_clip_edge=candidate.start_s <= 8.0 or asset.duration_s - candidate.end_s <= 8.0,
)
scored.append(
    candidate.model_copy(
        update={
            "quality_score": quality,
            "motion_score": motion_result.movement_score,
            "smoothness_score": motion_result.smoothness_score,
            "jitter_score": motion_result.jitter_score,
            "movement_score": motion_result.movement_score,
            "composition_score": motion_result.composition_score,
            "usability_score": motion_result.usability_score,
            "movement_type": motion_result.movement_type,
            "rejection_reason": rejection,
        }
    )
)
```

- [ ] **Step 5: Run tests**

Run:

```powershell
py -m pytest tests/analysis/test_motion.py tests/analysis/test_video.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src/aicutting/analysis/motion.py src/aicutting/analysis/video.py tests/analysis/test_motion.py
git commit -m "feat: score drone camera motion"
```

## Task 4: Add Director Engine Reports and Rejection Artifacts

**Files:**
- Create: `src/aicutting/director/engine.py`
- Modify: `src/aicutting/pipeline.py`
- Test: `tests/director/test_engine.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

Create `tests/director/test_engine.py`:

```python
from pathlib import Path

from aicutting.core.models import AnalysisReport, AudioAnalysis, ClipCandidate, MediaAsset
from aicutting.director.engine import build_director_outputs


def _candidate(start: float, rejection: str | None = None, usability: float = 0.8) -> ClipCandidate:
    return ClipCandidate(
        asset_path=Path("clip.mp4"),
        start_s=start,
        end_s=start + 5,
        quality_score=0.8,
        motion_score=0.7,
        diversity_key=f"clip:{int(start)}",
        usability_score=usability,
        movement_type="push_in" if rejection is None else "shaky",
        rejection_reason=rejection,
    )


def test_director_outputs_remove_rejected_segments_and_explain_them() -> None:
    report = AnalysisReport(
        media=[MediaAsset(path=Path("clip.mp4"), duration_s=40, width=1920, height=1080, fps=25)],
        candidates=[
            _candidate(0, "takeoff_or_landing_motion", usability=0.1),
            _candidate(10, None, usability=0.9),
        ],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )

    outputs = build_director_outputs(report)

    assert [candidate.start_s for candidate in outputs.analysis.candidates] == [10]
    assert outputs.rejected_segments[0].reason == "takeoff_or_landing_motion"
    assert outputs.director_report.decisions[0].selected is True
```

Extend `tests/test_pipeline.py` with:

```python
def test_pipeline_writes_director_artifacts(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")

    report = AnalysisReport(
        media=[MediaAsset(path=video, duration_s=8, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(
                asset_path=video,
                start_s=0,
                end_s=5,
                quality_score=0.9,
                motion_score=0.2,
                diversity_key="clip:0",
            )
        ],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )
    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: report,
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )

    CutPipeline(dependencies=deps).cut(
        input_dir=input_dir,
        music_path=None,
        output_dir=output_dir,
        dry_run=True,
    )

    assert (output_dir / "director-report.json").exists()
    assert (output_dir / "rejected-segments.json").exists()
    assert (output_dir / "location-suggestions.json").exists()
```

Use the existing fake dependency pattern in the file.

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
py -m pytest tests/director/test_engine.py tests/test_pipeline.py::test_pipeline_writes_director_artifacts -q
```

Expected: FAIL because director outputs and artifact writing do not exist.

- [ ] **Step 3: Implement director outputs**

Create `src/aicutting/director/engine.py`:

```python
from dataclasses import dataclass

from aicutting.core.models import AnalysisReport
from aicutting.director.models import DirectorDecision, DirectorReport, RejectedSegment


@dataclass(frozen=True)
class DirectorOutputs:
    analysis: AnalysisReport
    director_report: DirectorReport
    rejected_segments: list[RejectedSegment]


def build_director_outputs(report: AnalysisReport) -> DirectorOutputs:
    accepted = []
    rejected = []
    decisions = []
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
    filtered = report.model_copy(update={"candidates": accepted or report.candidates})
    warnings = [] if accepted else ["All candidates were rejected; using fallback candidates."]
    return DirectorOutputs(
        analysis=filtered,
        director_report=DirectorReport(decisions=decisions, warnings=warnings),
        rejected_segments=rejected,
    )
```

Modify `src/aicutting/pipeline.py` to call `build_director_outputs(report)` after analysis, plan with `director_outputs.analysis`, and write:

```python
write_json_model(output_dir / "director-report.json", director_outputs.director_report)
write_json_model(output_dir / "rejected-segments.json", director_outputs.rejected_segments)
```

For list serialization, add or reuse an artifact helper that can write plain Pydantic model lists deterministically.

- [ ] **Step 4: Run tests**

Run:

```powershell
py -m pytest tests/director/test_engine.py tests/test_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/aicutting/director/engine.py src/aicutting/pipeline.py tests/director/test_engine.py tests/test_pipeline.py
git commit -m "feat: write director rejection artifacts"
```

## Task 5: Implement Location Suggestions and Confidence Gate

**Files:**
- Create: `src/aicutting/director/location.py`
- Modify: `src/aicutting/pipeline.py`
- Test: `tests/director/test_location.py`

- [ ] **Step 1: Write failing tests**

Create `tests/director/test_location.py`:

```python
from aicutting.director.location import choose_renderable_title, fallback_location_suggestion
from aicutting.director.models import LocationSuggestion


def test_low_confidence_location_suggestion_is_not_renderable() -> None:
    suggestion = LocationSuggestion(
        title="Some Coast",
        place="unknown",
        confidence=0.4,
        evidence=["agent guess"],
        should_render=True,
    )

    assert choose_renderable_title([suggestion]) is None


def test_high_confidence_location_suggestion_becomes_title() -> None:
    suggestion = LocationSuggestion(
        title="Madeira Coast",
        place="Madeira, Portugal",
        confidence=0.86,
        evidence=["metadata GPS"],
        should_render=True,
    )

    title = choose_renderable_title([suggestion])

    assert title is not None
    assert title.title == "Madeira Coast"
    assert title.subtitle == "Madeira, Portugal"


def test_fallback_location_suggestion_is_safe_and_not_rendered() -> None:
    suggestion = fallback_location_suggestion("no metadata or agent backend available")

    assert suggestion.should_render is False
    assert suggestion.renderable is False
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
py -m pytest tests/director/test_location.py -q
```

Expected: FAIL because location module does not exist.

- [ ] **Step 3: Implement confidence gate**

Create `src/aicutting/director/location.py`:

```python
from aicutting.core.models import LocationTitle
from aicutting.director.models import LocationSuggestion


def choose_renderable_title(suggestions: list[LocationSuggestion]) -> LocationTitle | None:
    renderable = [suggestion for suggestion in suggestions if suggestion.renderable]
    if not renderable:
        return None
    best = max(renderable, key=lambda suggestion: suggestion.confidence)
    return LocationTitle(title=best.title, subtitle=best.place, confidence=best.confidence)


def fallback_location_suggestion(reason: str) -> LocationSuggestion:
    return LocationSuggestion(
        title="",
        place="unknown",
        confidence=0.0,
        evidence=[reason],
        should_render=False,
    )
```

Modify pipeline to always write `location-suggestions.json`; first implementation may write the fallback suggestion when no metadata/agent result exists.

- [ ] **Step 4: Run tests**

Run:

```powershell
py -m pytest tests/director/test_location.py tests/test_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/aicutting/director/location.py src/aicutting/pipeline.py tests/director/test_location.py tests/test_pipeline.py
git commit -m "feat: add confidence gated location titles"
```

## Task 6: Add Title Overlay Renderer

**Files:**
- Create: `src/aicutting/render/titles.py`
- Modify: `src/aicutting/render/ffmpeg.py`
- Modify: `src/aicutting/core/models.py`
- Test: `tests/render/test_titles.py`
- Test: `tests/render/test_ffmpeg.py`

- [ ] **Step 1: Write failing tests**

Create `tests/render/test_titles.py`:

```python
from pathlib import Path

from aicutting.core.models import LocationTitle
from aicutting.render.titles import build_drawtext_filter, escape_drawtext_text


def test_escape_drawtext_text_handles_special_characters() -> None:
    assert escape_drawtext_text("Madeira: Coast's Edge") == "Madeira\\: Coast\\'s Edge"


def test_build_drawtext_filter_uses_title_and_subtitle() -> None:
    title = LocationTitle(title="Madeira Coast", subtitle="Portugal", confidence=0.9)

    filter_text = build_drawtext_filter(title, font_path=Path("C:/Windows/Fonts/arial.ttf"))

    assert "drawtext=" in filter_text
    assert "Madeira Coast" in filter_text
    assert "Portugal" in filter_text
```

Add to `tests/render/test_ffmpeg.py`:

```python
def test_build_ffmpeg_command_adds_title_overlay_when_present() -> None:
    timeline = _timeline()
    timeline = timeline.model_copy(
        update={"title": LocationTitle(title="Madeira Coast", subtitle="Portugal", confidence=0.9)}
    )
    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]
    assert "drawtext=" in filter_complex
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
py -m pytest tests/render/test_titles.py tests/render/test_ffmpeg.py::test_build_ffmpeg_command_adds_title_overlay_when_present -q
```

Expected: FAIL because title module and timeline title field do not exist.

- [ ] **Step 3: Implement title overlay**

Add to `Timeline` in `src/aicutting/core/models.py`:

```python
title: LocationTitle | None = None
```

Create `src/aicutting/render/titles.py`:

```python
from pathlib import Path

from aicutting.core.models import LocationTitle


def escape_drawtext_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def build_drawtext_filter(title: LocationTitle, font_path: Path | None) -> str:
    font = f":fontfile='{font_path.as_posix()}'" if font_path else ""
    title_text = escape_drawtext_text(title.title)
    subtitle = escape_drawtext_text(title.subtitle or "")
    main = (
        "drawtext="
        f"text='{title_text}'{font}:fontsize=54:fontcolor=white:"
        "x=80:y=h-190:shadowcolor=black:shadowx=2:shadowy=2"
    )
    if not subtitle:
        return main
    sub = (
        "drawtext="
        f"text='{subtitle}'{font}:fontsize=30:fontcolor=white:"
        "x=82:y=h-126:shadowcolor=black:shadowx=2:shadowy=2"
    )
    return f"{main},{sub}"
```

Modify `build_ffmpeg_command` to append title filters after transition composition:

```python
if timeline.title is not None:
    filter_complex = f"{filter_complex};[vout]{build_drawtext_filter(timeline.title, discover_font())}[vout]"
```

If label reuse causes FFmpeg ambiguity, use `[vbase]` then `[vout]`.

- [ ] **Step 4: Run tests**

Run:

```powershell
py -m pytest tests/render/test_titles.py tests/render/test_ffmpeg.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/aicutting/core/models.py src/aicutting/render/titles.py src/aicutting/render/ffmpeg.py tests/render/test_titles.py tests/render/test_ffmpeg.py
git commit -m "feat: render confidence gated location titles"
```

## Task 7: Integrate Director Timeline and Full Artifacts

**Files:**
- Modify: `src/aicutting/director/engine.py`
- Modify: `src/aicutting/pipeline.py`
- Modify: `src/aicutting/planning/ranking.py`
- Test: `tests/director/test_engine.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

Extend `tests/director/test_engine.py`:

```python
def test_director_outputs_attach_high_confidence_title_to_plan_input() -> None:
    report = AnalysisReport(
        media=[MediaAsset(path=Path("clip.mp4"), duration_s=40, width=1920, height=1080, fps=25)],
        candidates=[_candidate(10, None, usability=0.9)],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )
    suggestion = LocationSuggestion(
        title="Madeira Coast",
        place="Madeira, Portugal",
        confidence=0.86,
        evidence=["metadata GPS"],
        should_render=True,
    )

    outputs = build_director_outputs(report, location_suggestions=[suggestion])

    assert outputs.analysis.candidates[0].start_s == 10
    assert outputs.director_report.title is not None
    assert outputs.director_report.title.title == "Madeira Coast"
```

The assertion should prove `DirectorOutputs.analysis` retains accepted candidates and `DirectorReport.title` is available when a high-confidence suggestion exists.

Extend `tests/planning/test_ranking.py`:

```python
def test_rank_candidates_prefers_usability_when_available() -> None:
    technically_clean_but_bad_motion = ClipCandidate(
        asset_path=Path("clean.mp4"),
        start_s=0,
        end_s=5,
        quality_score=0.95,
        motion_score=0.2,
        diversity_key="clean:0",
        usability_score=0.25,
    )
    usable_drone_move = ClipCandidate(
        asset_path=Path("usable.mp4"),
        start_s=10,
        end_s=15,
        quality_score=0.75,
        motion_score=0.6,
        diversity_key="usable:1",
        usability_score=0.92,
    )

    ranked = rank_candidates([technically_clean_but_bad_motion, usable_drone_move])

    assert ranked[0] == usable_drone_move
```

Use two candidates where lower visual composite but high usability wins.

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
py -m pytest tests/director/test_engine.py tests/planning/test_ranking.py::test_rank_candidates_prefers_usability_when_available -q
```

Expected: FAIL because ranking and title propagation are not complete.

- [ ] **Step 3: Implement integration**

Modify ranking key:

```python
ranked = sorted(candidates, key=lambda candidate: candidate.director_score, reverse=True)
```

Modify pipeline:

```python
director_outputs = build_director_outputs(report, location_suggestions=suggestions)
plan = build_cut_plan(director_outputs.analysis)
if director_outputs.director_report.title is not None:
    plan = plan.model_copy(
        update={"timeline": plan.timeline.model_copy(update={"title": director_outputs.director_report.title})}
    )
```

Write all director artifacts before render.

- [ ] **Step 4: Run tests**

Run:

```powershell
py -m pytest tests/director tests/planning tests/test_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/aicutting/director/engine.py src/aicutting/pipeline.py src/aicutting/planning/ranking.py tests/director tests/planning/test_ranking.py tests/test_pipeline.py
git commit -m "feat: integrate director timeline artifacts"
```

## Task 8: Final Verification and Real Preview

**Files:**
- No source files unless verification finds a real bug.

- [ ] **Step 1: Run full automated verification**

Run:

```powershell
py -m pytest -q
py -m ruff check .
py -m mypy src
```

Expected:

```text
all tests pass
All checks passed!
Success: no issues found
```

- [ ] **Step 2: Run a real dry-run on the user's sample folder**

Run:

```powershell
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
py -m aicutting cut 'C:\Users\mrnix\Downloads\est' --music 'C:\Users\mrnix\Downloads\etss\videoplayback.mp3' --out 'C:\Users\mrnix\Downloads\est-aicutting-director-dry' --dry-run
```

Expected output folder contains:

- `analysis.json`
- `cut-plan.json`
- `timeline.json`
- `director-report.json`
- `rejected-segments.json`
- `location-suggestions.json`
- `resolve/`

- [ ] **Step 3: Inspect director artifacts**

Run:

```powershell
$rejected = Get-Content -Raw 'C:\Users\mrnix\Downloads\est-aicutting-director-dry\rejected-segments.json' | ConvertFrom-Json
$timeline = Get-Content -Raw 'C:\Users\mrnix\Downloads\est-aicutting-director-dry\timeline.json' | ConvertFrom-Json
[pscustomobject]@{
  RejectedCount = @($rejected).Count
  ClipCount = @($timeline.clips).Count
  FirstStarts = (($timeline.clips | Select-Object -First 8 | ForEach-Object { $_.source_start_s }) -join ', ')
} | ConvertTo-Json
```

Expected: rejected count is non-zero for bad motion if sample footage contains takeoff, landing, search-flight, or shaky segments; timeline start times are not just `0`.

- [ ] **Step 4: Render a short verified preview**

Run:

```powershell
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
@'
from pathlib import Path
from aicutting.core.artifacts import read_json_model
from aicutting.core.models import AnalysisReport, Timeline
from aicutting.planning.engine import build_cut_plan
from aicutting.render.ffmpeg import render_timeline

report = read_json_model(Path(r'C:\Users\mrnix\Downloads\est-aicutting-director-dry\analysis.json'), AnalysisReport)
plan = build_cut_plan(report)
preview_clips = plan.timeline.clips[:5]
preview_duration = round(sum(clip.timeline_duration_s for clip in preview_clips), 3)
preview = Timeline(
    target_duration_s=preview_duration,
    clips=preview_clips,
    fps=plan.timeline.fps,
    width=plan.timeline.width,
    height=plan.timeline.height,
    title=plan.timeline.title,
)
out = Path(r'C:\Users\mrnix\Downloads\est-aicutting-director-preview')
out.mkdir(parents=True, exist_ok=True)
render_timeline(preview, out / 'final-preview.mp4', report.audio.path)
print(out / 'final-preview.mp4')
print(f'duration={preview_duration}')
'@ | py -
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height -of json 'C:\Users\mrnix\Downloads\est-aicutting-director-preview\final-preview.mp4'
```

Expected: output MP4 has video and audio streams and duration within one second of the preview timeline duration.

- [ ] **Step 5: Commit any verification-only fixes**

If real verification uncovers a bug, fix it with a failing test first, then commit:

```powershell
git add src/aicutting tests
git commit -m "fix: stabilize director preview render"
```

## Plan Self-Review Checklist

- [ ] Spec coverage: motion scoring, hard rejection, beat timing, location confidence, title rendering, transitions, and artifacts all have tasks.
- [ ] Placeholder scan: no `TBD`, `TODO`, `implement later`, or vague "handle appropriately" steps remain.
- [ ] Type consistency: `LocationTitle`, `LocationSuggestion`, `DirectorReport`, `DirectorOutputs`, and candidate fields are introduced before later tasks use them.
- [ ] Test-first flow: every production task starts with failing tests and expected failure.
- [ ] Dirty worktree safety: existing foundation fixes are verified and committed before new Director Engine work begins.
