# AI Drone Director 2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first production-quality AI Drone Director 2.0 slice: better drone raw-moment selection, beat-aware story planning, motion-aware effect decisions, and auditable 2.0 artifacts.

**Architecture:** Keep `CutPipeline` as the entry point. Extend existing Pydantic models and add focused modules under `analysis`, `director`, and `planning` rather than replacing the whole pipeline. Ship 2.0 as deterministic local analysis first; optional local agent review remains additive and outside this implementation plan.

**Tech Stack:** Python 3.11+, Pydantic, OpenCV, NumPy, librosa, FFmpeg command construction, pytest, ruff, mypy.

---

## File Structure

- Modify `src/aicutting/core/models.py`
  Add drone shot type, richer clip scoring fields, new transition enum values, and optional timeline/effect metadata.

- Create `src/aicutting/director/drone_models.py`
  Pydantic artifact models for `shot-candidates.json`, `beat-plan.json`, `story-plan.json`, `effect-plan.json`, and `director-2-report.json`.

- Create `src/aicutting/analysis/drone_shots.py`
  Deterministic frame-sequence analysis for drone shot type, reveal score, novelty score, motion intent, and hard rejection reason.

- Modify `src/aicutting/analysis/video.py`
  Generate denser candidates and trim weak heads/tails before scoring long raw drone clips.

- Create `src/aicutting/analysis/beat_plan.py`
  Convert `AudioAnalysis` into sectioned beat and energy planning data.

- Create `src/aicutting/planning/story.py`
  Build an edit arc from selected candidates: establish, move, peak, release.

- Create `src/aicutting/planning/effects.py`
  Choose motion-aware transitions and effect decisions from previous/current shots and beat context.

- Modify `src/aicutting/planning/engine.py`
  Use story/effect planning instead of flat ranking when 2.0 data is available.

- Modify `src/aicutting/render/ffmpeg.py`
  Render new transition enum values with stable FFmpeg fallbacks.

- Modify `src/aicutting/pipeline.py`
  Write the new 2.0 artifacts while preserving existing artifacts.

---

### Task 1: Add Drone Director 2.0 Models

**Files:**
- Modify: `src/aicutting/core/models.py`
- Create: `src/aicutting/director/drone_models.py`
- Test: `tests/core/test_models.py`
- Test: `tests/director/test_drone_models.py`

- [ ] **Step 1: Write failing core model tests**

Add to `tests/core/test_models.py`:

```python
def test_clip_candidate_exposes_drone_director_score() -> None:
    candidate = ClipCandidate(
        asset_path=Path("clip.mp4"),
        start_s=2.0,
        end_s=7.0,
        quality_score=0.8,
        motion_score=0.7,
        diversity_key="clip:0",
        shot_type=DroneShotType.REVEAL,
        technical_score=0.75,
        motion_intent_score=0.9,
        reveal_score=0.85,
        novelty_score=0.6,
        drone_director_score=0.88,
    )

    assert candidate.shot_type == DroneShotType.REVEAL
    assert candidate.director_score == 0.88
```

Add to the imports:

```python
from aicutting.core.models import ClipCandidate, DroneShotType
```

- [ ] **Step 2: Write failing artifact model tests**

Create `tests/director/test_drone_models.py`:

```python
from pathlib import Path

from aicutting.core.models import DroneShotType, TransitionType
from aicutting.director.drone_models import (
    BeatPlan,
    BeatSection,
    EffectDecision,
    EffectPlan,
    ShotCandidateArtifact,
    StoryPlan,
    StoryPlanClip,
)


def test_shot_candidate_artifact_records_drone_reasoning() -> None:
    artifact = ShotCandidateArtifact(
        asset_path=Path("clip.mp4"),
        start_s=3.0,
        end_s=8.0,
        shot_type=DroneShotType.REVEAL,
        selected=True,
        rejected=False,
        rejection_reason=None,
        technical_score=0.8,
        stability_score=0.9,
        composition_score=0.75,
        motion_intent_score=0.86,
        reveal_score=0.91,
        novelty_score=0.6,
        drone_director_score=0.87,
        reasons=["smooth reveal", "strong stability"],
    )

    assert artifact.duration_s == 5.0
    assert artifact.reasons[0] == "smooth reveal"


def test_beat_story_and_effect_models_are_serializable() -> None:
    beat_plan = BeatPlan(
        beats_s=[0.0, 1.0, 2.0],
        downbeats_s=[0.0, 2.0],
        phrase_boundaries_s=[0.0, 4.0],
        energy_curve=[0.2, 0.8],
        sections=[BeatSection(label="peak", start_s=1.0, end_s=3.0, energy=0.8, cut_density=0.8)],
    )
    story = StoryPlan(
        target_duration_s=12.0,
        clips=[
            StoryPlanClip(
                asset_path=Path("clip.mp4"),
                source_start_s=3.0,
                source_end_s=7.0,
                role="peak",
                shot_type=DroneShotType.REVEAL,
                beat_anchor_s=4.0,
                reason="best reveal at peak",
            )
        ],
    )
    effects = EffectPlan(
        decisions=[
            EffectDecision(
                clip_index=0,
                transition=TransitionType.SMOOTH_ZOOM,
                duration_s=0.25,
                confidence=0.86,
                beat_anchor_s=4.0,
                reason="approach motion at peak",
            )
        ]
    )

    assert beat_plan.sections[0].label == "peak"
    assert story.clips[0].role == "peak"
    assert effects.decisions[0].transition == TransitionType.SMOOTH_ZOOM
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
py -m pytest tests\core\test_models.py tests\director\test_drone_models.py -q
```

Expected: FAIL because `DroneShotType`, new fields, and `drone_models.py` do not exist.

- [ ] **Step 4: Implement core model additions**

In `src/aicutting/core/models.py`, add before `LocationTitle`:

```python
class DroneShotType(StrEnum):
    REVEAL = "reveal"
    APPROACH = "approach"
    PULL_BACK = "pull_back"
    ORBIT = "orbit"
    FLY_THROUGH = "fly_through"
    TOP_DOWN = "top_down"
    ESTABLISHING = "establishing"
    TRACKING = "tracking"
    SEARCH_MOTION = "search_motion"
    TAKEOFF_OR_LANDING = "takeoff_or_landing"
    UNSTABLE = "unstable"
    UNKNOWN = "unknown"
```

Extend `ClipCandidate`:

```python
    shot_type: DroneShotType = DroneShotType.UNKNOWN
    technical_score: float | None = Field(default=None, ge=0, le=1)
    motion_intent_score: float | None = Field(default=None, ge=0, le=1)
    reveal_score: float | None = Field(default=None, ge=0, le=1)
    novelty_score: float | None = Field(default=None, ge=0, le=1)
    drone_director_score: float | None = Field(default=None, ge=0, le=1)
```

Change `director_score`:

```python
    @property
    def director_score(self) -> float:
        if self.drone_director_score is not None:
            return round(self.drone_director_score, 6)
        usability = (
            self.usability_score if self.usability_score is not None else self.composite_score
        )
        return round((self.composite_score * 0.35) + (usability * 0.65), 6)
```

Extend `TransitionType`:

```python
    SMOOTH_ZOOM = "smooth_zoom"
    WHIP_BLUR = "whip_blur"
    FLASH_CUT = "flash_cut"
    SPEED_RAMP = "speed_ramp"
    MATCH_MOTION = "match_motion"
```

- [ ] **Step 5: Implement artifact models**

Create `src/aicutting/director/drone_models.py`:

```python
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, ValidationInfo

from aicutting.core.models import DroneShotType, TransitionType


class ShotCandidateArtifact(BaseModel):
    asset_path: Path
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    shot_type: DroneShotType
    selected: bool
    rejected: bool
    rejection_reason: str | None
    technical_score: float = Field(ge=0, le=1)
    stability_score: float = Field(ge=0, le=1)
    composition_score: float = Field(ge=0, le=1)
    motion_intent_score: float = Field(ge=0, le=1)
    reveal_score: float = Field(ge=0, le=1)
    novelty_score: float = Field(ge=0, le=1)
    drone_director_score: float = Field(ge=0, le=1)
    reasons: list[str]

    @field_validator("end_s")
    @classmethod
    def end_must_follow_start(cls, value: float, info: ValidationInfo) -> float:
        start = info.data.get("start_s", 0.0)
        if value <= start:
            raise ValueError("end_s must be greater than start_s")
        return value

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


class BeatSection(BaseModel):
    label: str
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    energy: float = Field(ge=0, le=1)
    cut_density: float = Field(ge=0, le=1)


class BeatPlan(BaseModel):
    beats_s: list[float]
    downbeats_s: list[float]
    phrase_boundaries_s: list[float]
    energy_curve: list[float]
    sections: list[BeatSection]


class StoryPlanClip(BaseModel):
    asset_path: Path
    source_start_s: float = Field(ge=0)
    source_end_s: float = Field(gt=0)
    role: str
    shot_type: DroneShotType
    beat_anchor_s: float | None = Field(default=None, ge=0)
    reason: str


class StoryPlan(BaseModel):
    target_duration_s: float = Field(gt=0)
    clips: list[StoryPlanClip]


class EffectDecision(BaseModel):
    clip_index: int = Field(ge=0)
    transition: TransitionType
    duration_s: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    beat_anchor_s: float | None = Field(default=None, ge=0)
    reason: str


class EffectPlan(BaseModel):
    decisions: list[EffectDecision]


class Director2Report(BaseModel):
    selected_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    average_drone_director_score: float = Field(ge=0, le=1)
    warnings: list[str]
```

- [ ] **Step 6: Run tests**

Run:

```powershell
py -m pytest tests\core\test_models.py tests\director\test_drone_models.py -q
py -m ruff check src\aicutting\core\models.py src\aicutting\director\drone_models.py tests\core\test_models.py tests\director\test_drone_models.py
py -m mypy src
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add src\aicutting\core\models.py src\aicutting\director\drone_models.py tests\core\test_models.py tests\director\test_drone_models.py
git commit -m "feat: add drone director 2.0 models"
```

---

### Task 2: Add Drone Shot Intelligence Scoring

**Files:**
- Create: `src/aicutting/analysis/drone_shots.py`
- Modify: `src/aicutting/analysis/video.py`
- Test: `tests/analysis/test_drone_shots.py`
- Test: `tests/analysis/test_video.py`

- [ ] **Step 1: Write failing drone shot tests**

Create `tests/analysis/test_drone_shots.py`:

```python
import numpy as np

from aicutting.analysis.drone_shots import analyze_drone_shot_frames
from aicutting.core.models import DroneShotType


def _frame(center_x: int, center_y: int, size: int = 96) -> np.ndarray:
    frame = np.zeros((size, size, 3), dtype=np.uint8)
    frame[max(0, center_y - 8) : center_y + 8, max(0, center_x - 8) : center_x + 8] = 255
    return frame


def test_classifies_smooth_reveal_with_high_director_score() -> None:
    frames = [_frame(18, 48), _frame(34, 48), _frame(52, 48), _frame(70, 48)]

    result = analyze_drone_shot_frames(frames, starts_near_clip_edge=False)

    assert result.shot_type == DroneShotType.REVEAL
    assert result.rejection_reason is None
    assert result.drone_director_score >= 0.7
    assert "smooth" in " ".join(result.reasons)


def test_rejects_search_motion_with_direction_changes() -> None:
    frames = [_frame(18, 48), _frame(74, 48), _frame(24, 48), _frame(72, 48)]

    result = analyze_drone_shot_frames(frames, starts_near_clip_edge=False)

    assert result.shot_type == DroneShotType.SEARCH_MOTION
    assert result.rejection_reason == "search_flight_before_subject"
    assert result.drone_director_score < 0.5


def test_rejects_jitter_near_edges_as_takeoff_or_landing() -> None:
    frames = [_frame(48, 10), _frame(20, 72), _frame(70, 18), _frame(30, 80)]

    result = analyze_drone_shot_frames(frames, starts_near_clip_edge=True)

    assert result.shot_type == DroneShotType.TAKEOFF_OR_LANDING
    assert result.rejection_reason == "takeoff_or_landing_motion"
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
py -m pytest tests\analysis\test_drone_shots.py -q
```

Expected: FAIL because `aicutting.analysis.drone_shots` does not exist.

- [ ] **Step 3: Implement deterministic drone shot scoring**

Create `src/aicutting/analysis/drone_shots.py`:

```python
from dataclasses import dataclass

import numpy as np

from aicutting.analysis.motion import analyze_motion_frames, reject_bad_motion
from aicutting.core.models import DroneShotType


@dataclass(frozen=True)
class DroneShotAnalysis:
    shot_type: DroneShotType
    technical_score: float
    stability_score: float
    composition_score: float
    motion_intent_score: float
    reveal_score: float
    novelty_score: float
    drone_director_score: float
    rejection_reason: str | None
    reasons: list[str]


def analyze_drone_shot_frames(
    frames: list[np.ndarray],
    starts_near_clip_edge: bool,
) -> DroneShotAnalysis:
    motion = analyze_motion_frames(frames)
    rejection = reject_bad_motion(motion, starts_near_clip_edge=starts_near_clip_edge)
    reveal = _reveal_score(frames)
    novelty = _novelty_score(frames)
    technical = _technical_score(frames)
    motion_intent = max(0.0, min(1.0, (motion.smoothness_score * 0.6) + (motion.movement_score * 0.4)))
    shot_type = _shot_type(motion.movement_type, reveal, rejection)
    if rejection == "takeoff_or_landing_motion":
        shot_type = DroneShotType.TAKEOFF_OR_LANDING
    elif rejection == "search_flight_before_subject":
        shot_type = DroneShotType.SEARCH_MOTION
    elif rejection is not None:
        shot_type = DroneShotType.UNSTABLE

    score = round(
        (technical * 0.18)
        + (motion.smoothness_score * 0.24)
        + (motion.composition_score * 0.18)
        + (motion_intent * 0.18)
        + (reveal * 0.14)
        + (novelty * 0.08),
        6,
    )
    if rejection is not None:
        score = round(min(score, 0.45), 6)

    reasons = [
        f"{shot_type.value} motion",
        f"smoothness {motion.smoothness_score:.2f}",
        f"reveal {reveal:.2f}",
    ]
    if rejection:
        reasons.append(rejection)

    return DroneShotAnalysis(
        shot_type=shot_type,
        technical_score=technical,
        stability_score=motion.smoothness_score,
        composition_score=motion.composition_score,
        motion_intent_score=round(motion_intent, 6),
        reveal_score=reveal,
        novelty_score=novelty,
        drone_director_score=score,
        rejection_reason=rejection,
        reasons=reasons,
    )


def _shot_type(movement_type: str, reveal_score: float, rejection: str | None) -> DroneShotType:
    if rejection is not None:
        return DroneShotType.UNSTABLE
    if reveal_score >= 0.6:
        return DroneShotType.REVEAL
    if movement_type == "hover":
        return DroneShotType.ESTABLISHING
    if movement_type in {"pan_left", "pan_right"}:
        return DroneShotType.TRACKING
    if movement_type == "tilt_down":
        return DroneShotType.TOP_DOWN
    if movement_type == "tilt_up":
        return DroneShotType.PULL_BACK
    if movement_type == "push_in":
        return DroneShotType.APPROACH
    return DroneShotType.UNKNOWN


def _technical_score(frames: list[np.ndarray]) -> float:
    if not frames:
        return 0.0
    values = [float(frame.std()) / 80.0 for frame in frames]
    return round(max(0.0, min(1.0, float(np.mean(values)))), 6)


def _reveal_score(frames: list[np.ndarray]) -> float:
    if len(frames) < 2:
        return 0.0
    first = frames[0].astype(np.float32)
    last = frames[-1].astype(np.float32)
    delta = float(np.mean(np.abs(last - first))) / 80.0
    return round(max(0.0, min(1.0, delta)), 6)


def _novelty_score(frames: list[np.ndarray]) -> float:
    if len(frames) < 2:
        return 0.0
    diffs = [
        float(np.mean(np.abs(current.astype(np.float32) - previous.astype(np.float32)))) / 90.0
        for previous, current in zip(frames, frames[1:], strict=False)
    ]
    return round(max(0.0, min(1.0, float(np.mean(diffs)))), 6)
```

- [ ] **Step 4: Update video scoring to attach drone shot fields**

In `src/aicutting/analysis/video.py`, import:

```python
from aicutting.analysis.drone_shots import analyze_drone_shot_frames
```

Inside `score_candidates_from_video`, replace the `motion_result` scoring block with:

```python
            motion_result = analyze_motion_frames(frames)
            drone_result = analyze_drone_shot_frames(
                frames,
                starts_near_clip_edge=(
                    candidate.start_s <= 8.0 or asset.duration_s - candidate.end_s <= 8.0
                ),
            )
            scored.append(
                candidate.model_copy(
                    update={
                        "quality_score": quality,
                        "motion_score": motion_result.movement_score,
                        "smoothness_score": motion_result.smoothness_score,
                        "jitter_score": motion_result.jitter_score,
                        "movement_score": motion_result.movement_score,
                        "composition_score": drone_result.composition_score,
                        "usability_score": motion_result.usability_score,
                        "movement_type": motion_result.movement_type,
                        "shot_type": drone_result.shot_type,
                        "technical_score": drone_result.technical_score,
                        "motion_intent_score": drone_result.motion_intent_score,
                        "reveal_score": drone_result.reveal_score,
                        "novelty_score": drone_result.novelty_score,
                        "drone_director_score": drone_result.drone_director_score,
                        "rejection_reason": drone_result.rejection_reason,
                    }
                )
            )
```

Remove the now-unused `reject_bad_motion` import.

- [ ] **Step 5: Add integration test to `tests/analysis/test_video.py`**

Add:

```python
def test_score_candidates_from_video_attaches_drone_director_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    video = tmp_path / "clip.mp4"
    video.write_text("", encoding="utf-8")
    asset = MediaAsset(path=video, duration_s=10.0, width=1920, height=1080, fps=25.0)
    candidate = ClipCandidate(
        asset_path=video,
        start_s=2.0,
        end_s=7.0,
        quality_score=0.5,
        motion_score=0.5,
        diversity_key="clip:0",
    )

    class FakeCapture:
        def isOpened(self) -> bool:
            return True

        def set(self, prop: int, value: float) -> None:
            del prop, value

        def read(self) -> tuple[bool, np.ndarray]:
            frame = np.zeros((96, 96, 3), dtype=np.uint8)
            frame[:, 40:60] = 255
            return True, frame

        def release(self) -> None:
            pass

    monkeypatch.setattr("aicutting.analysis.video.cv2.VideoCapture", lambda _: FakeCapture())

    scored = score_candidates_from_video(asset, [candidate])

    assert scored[0].shot_type != DroneShotType.UNKNOWN
    assert scored[0].drone_director_score is not None
```

Add imports if missing:

```python
import numpy as np
import pytest
from pathlib import Path
from aicutting.core.models import ClipCandidate, DroneShotType, MediaAsset
```

- [ ] **Step 6: Run tests and commit**

```powershell
py -m pytest tests\analysis\test_drone_shots.py tests\analysis\test_video.py -q
py -m ruff check src\aicutting\analysis\drone_shots.py src\aicutting\analysis\video.py tests\analysis\test_drone_shots.py tests\analysis\test_video.py
py -m mypy src
git add src\aicutting\analysis\drone_shots.py src\aicutting\analysis\video.py tests\analysis\test_drone_shots.py tests\analysis\test_video.py
git commit -m "feat: score drone shot intelligence"
```

---

### Task 3: Add Beat Plan 2.0

**Files:**
- Create: `src/aicutting/analysis/beat_plan.py`
- Test: `tests/analysis/test_beat_plan.py`

- [ ] **Step 1: Write failing tests**

Create `tests/analysis/test_beat_plan.py`:

```python
from aicutting.analysis.beat_plan import build_beat_plan
from aicutting.core.models import AudioAnalysis


def test_build_beat_plan_groups_energy_sections() -> None:
    audio = AudioAnalysis(
        path=None,
        duration_s=12.0,
        beats_s=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
        energy=[0.1, 0.2, 0.6, 0.9, 0.85, 0.5, 0.2, 0.1],
    )

    plan = build_beat_plan(audio)

    assert plan.downbeats_s == [0.0, 4.0]
    assert plan.phrase_boundaries_s == [0.0]
    assert any(section.label == "peak" for section in plan.sections)
    assert max(section.cut_density for section in plan.sections) > 0.6


def test_build_beat_plan_handles_no_music() -> None:
    plan = build_beat_plan(AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[]))

    assert plan.beats_s == []
    assert plan.sections[0].label == "visual_default"
    assert plan.sections[0].cut_density == 0.35
```

- [ ] **Step 2: Run failing tests**

```powershell
py -m pytest tests\analysis\test_beat_plan.py -q
```

Expected: FAIL because `beat_plan.py` does not exist.

- [ ] **Step 3: Implement beat plan**

Create `src/aicutting/analysis/beat_plan.py`:

```python
from aicutting.core.models import AudioAnalysis
from aicutting.director.drone_models import BeatPlan, BeatSection


def build_beat_plan(audio: AudioAnalysis) -> BeatPlan:
    if not audio.beats_s:
        return BeatPlan(
            beats_s=[],
            downbeats_s=[],
            phrase_boundaries_s=[],
            energy_curve=[],
            sections=[BeatSection(label="visual_default", start_s=0.0, end_s=0.0, energy=0.2, cut_density=0.35)],
        )

    downbeats = [beat for index, beat in enumerate(audio.beats_s) if index % 4 == 0]
    phrase_boundaries = [beat for index, beat in enumerate(audio.beats_s) if index % 16 == 0]
    sections = _sections(audio)
    return BeatPlan(
        beats_s=audio.beats_s,
        downbeats_s=downbeats,
        phrase_boundaries_s=phrase_boundaries,
        energy_curve=audio.energy,
        sections=sections,
    )


def _sections(audio: AudioAnalysis) -> list[BeatSection]:
    if not audio.energy:
        return [BeatSection(label="steady", start_s=0.0, end_s=audio.duration_s, energy=0.35, cut_density=0.4)]
    section_count = min(4, max(1, len(audio.energy)))
    chunk_size = max(1, len(audio.energy) // section_count)
    sections: list[BeatSection] = []
    for index in range(section_count):
        start_i = index * chunk_size
        end_i = len(audio.energy) if index == section_count - 1 else min(len(audio.energy), (index + 1) * chunk_size)
        values = audio.energy[start_i:end_i]
        avg = sum(values) / len(values)
        label = _label(avg, index, section_count)
        start_s = round((start_i / len(audio.energy)) * max(audio.duration_s, 0.0), 3)
        end_s = round((end_i / len(audio.energy)) * max(audio.duration_s, 0.0), 3)
        sections.append(
            BeatSection(
                label=label,
                start_s=start_s,
                end_s=max(end_s, start_s + 0.001),
                energy=round(avg, 6),
                cut_density=round(_cut_density(avg), 6),
            )
        )
    return sections


def _label(energy: float, index: int, section_count: int) -> str:
    if energy >= 0.72:
        return "peak"
    if index == 0:
        return "intro"
    if index == section_count - 1:
        return "release"
    if energy >= 0.45:
        return "build"
    return "calm"


def _cut_density(energy: float) -> float:
    if energy >= 0.72:
        return 0.85
    if energy >= 0.45:
        return 0.6
    return 0.35
```

- [ ] **Step 4: Run tests and commit**

```powershell
py -m pytest tests\analysis\test_beat_plan.py -q
py -m ruff check src\aicutting\analysis\beat_plan.py tests\analysis\test_beat_plan.py
py -m mypy src
git add src\aicutting\analysis\beat_plan.py tests\analysis\test_beat_plan.py
git commit -m "feat: build drone director beat plans"
```

---

### Task 4: Add Story Planner 2.0

**Files:**
- Create: `src/aicutting/planning/story.py`
- Test: `tests/planning/test_story.py`

- [ ] **Step 1: Write failing tests**

Create `tests/planning/test_story.py`:

```python
from pathlib import Path

from aicutting.core.models import ClipCandidate, DroneShotType
from aicutting.director.drone_models import BeatPlan, BeatSection
from aicutting.planning.story import build_story_plan


def _candidate(start: float, shot_type: DroneShotType, score: float) -> ClipCandidate:
    return ClipCandidate(
        asset_path=Path(f"{shot_type.value}-{start}.mp4"),
        start_s=start,
        end_s=start + 5.0,
        quality_score=0.8,
        motion_score=0.7,
        diversity_key=f"{shot_type.value}:{start}",
        shot_type=shot_type,
        drone_director_score=score,
    )


def test_story_plan_prefers_drone_edit_arc() -> None:
    beat_plan = BeatPlan(
        beats_s=[0.0, 2.0, 4.0, 6.0, 8.0],
        downbeats_s=[0.0, 4.0, 8.0],
        phrase_boundaries_s=[0.0, 8.0],
        energy_curve=[0.2, 0.8],
        sections=[BeatSection(label="peak", start_s=0.0, end_s=10.0, energy=0.8, cut_density=0.85)],
    )
    candidates = [
        _candidate(0.0, DroneShotType.SEARCH_MOTION, 0.2),
        _candidate(5.0, DroneShotType.ESTABLISHING, 0.75),
        _candidate(10.0, DroneShotType.APPROACH, 0.8),
        _candidate(15.0, DroneShotType.REVEAL, 0.95),
        _candidate(20.0, DroneShotType.PULL_BACK, 0.76),
    ]

    plan = build_story_plan(candidates, beat_plan, target_duration_s=14.0)

    assert [clip.role for clip in plan.clips] == ["establish", "move", "peak", "release"]
    assert plan.clips[2].shot_type == DroneShotType.REVEAL
    assert plan.clips[2].beat_anchor_s in beat_plan.downbeats_s
    assert all(clip.shot_type != DroneShotType.SEARCH_MOTION for clip in plan.clips)
```

- [ ] **Step 2: Run failing tests**

```powershell
py -m pytest tests\planning\test_story.py -q
```

Expected: FAIL because `planning.story` does not exist.

- [ ] **Step 3: Implement story planner**

Create `src/aicutting/planning/story.py`:

```python
from pathlib import Path

from aicutting.core.models import ClipCandidate, DroneShotType
from aicutting.director.drone_models import BeatPlan, StoryPlan, StoryPlanClip

ROLE_PREFERENCES: dict[str, set[DroneShotType]] = {
    "establish": {DroneShotType.ESTABLISHING, DroneShotType.TOP_DOWN, DroneShotType.REVEAL},
    "move": {DroneShotType.APPROACH, DroneShotType.FLY_THROUGH, DroneShotType.TRACKING, DroneShotType.ORBIT},
    "peak": {DroneShotType.REVEAL, DroneShotType.APPROACH, DroneShotType.FLY_THROUGH},
    "release": {DroneShotType.PULL_BACK, DroneShotType.ESTABLISHING, DroneShotType.TOP_DOWN},
}

BAD_TYPES = {
    DroneShotType.SEARCH_MOTION,
    DroneShotType.TAKEOFF_OR_LANDING,
    DroneShotType.UNSTABLE,
}


def build_story_plan(
    candidates: list[ClipCandidate],
    beat_plan: BeatPlan,
    target_duration_s: float,
) -> StoryPlan:
    usable = [candidate for candidate in candidates if candidate.shot_type not in BAD_TYPES and not candidate.rejection_reason]
    if not usable:
        usable = sorted(candidates, key=lambda candidate: candidate.director_score, reverse=True)

    selected: list[StoryPlanClip] = []
    used_paths: set[Path] = set()
    for role in ("establish", "move", "peak", "release"):
        candidate = _pick_for_role(role, usable, used_paths)
        if candidate is None:
            continue
        used_paths.add(candidate.asset_path)
        selected.append(
            StoryPlanClip(
                asset_path=candidate.asset_path,
                source_start_s=candidate.start_s,
                source_end_s=candidate.end_s,
                role=role,
                shot_type=candidate.shot_type,
                beat_anchor_s=_beat_anchor(beat_plan, role),
                reason=f"{role}: {candidate.shot_type.value} score {candidate.director_score:.2f}",
            )
        )
    return StoryPlan(target_duration_s=target_duration_s, clips=selected)


def _pick_for_role(
    role: str,
    candidates: list[ClipCandidate],
    used_paths: set[Path],
) -> ClipCandidate | None:
    preferred = ROLE_PREFERENCES[role]
    pool = [candidate for candidate in candidates if candidate.asset_path not in used_paths]
    if not pool:
        pool = candidates
    return max(
        pool,
        key=lambda candidate: (
            candidate.shot_type in preferred,
            candidate.reveal_score or 0.0,
            candidate.director_score,
        ),
        default=None,
    )


def _beat_anchor(beat_plan: BeatPlan, role: str) -> float | None:
    if not beat_plan.downbeats_s:
        return None
    if role == "peak":
        return beat_plan.downbeats_s[min(len(beat_plan.downbeats_s) - 1, len(beat_plan.downbeats_s) // 2)]
    if role == "release":
        return beat_plan.downbeats_s[-1]
    return beat_plan.downbeats_s[0]
```

- [ ] **Step 4: Run tests and commit**

```powershell
py -m pytest tests\planning\test_story.py -q
py -m ruff check src\aicutting\planning\story.py tests\planning\test_story.py
py -m mypy src
git add src\aicutting\planning\story.py tests\planning\test_story.py
git commit -m "feat: plan drone story arcs"
```

---

### Task 5: Add Motion-Aware Effect Planning

**Files:**
- Create: `src/aicutting/planning/effects.py`
- Test: `tests/planning/test_effects.py`

- [ ] **Step 1: Write failing tests**

Create `tests/planning/test_effects.py`:

```python
from pathlib import Path

from aicutting.core.models import DroneShotType, TransitionType
from aicutting.director.drone_models import BeatPlan, BeatSection, StoryPlan, StoryPlanClip
from aicutting.planning.effects import build_effect_plan


def _clip(index: int, shot_type: DroneShotType, role: str) -> StoryPlanClip:
    return StoryPlanClip(
        asset_path=Path(f"clip-{index}.mp4"),
        source_start_s=float(index * 5),
        source_end_s=float(index * 5 + 4),
        role=role,
        shot_type=shot_type,
        beat_anchor_s=float(index * 2),
        reason=role,
    )


def test_effect_plan_uses_zoom_for_approach_peak() -> None:
    story = StoryPlan(
        target_duration_s=12.0,
        clips=[
            _clip(0, DroneShotType.ESTABLISHING, "establish"),
            _clip(1, DroneShotType.APPROACH, "move"),
            _clip(2, DroneShotType.REVEAL, "peak"),
        ],
    )
    beat_plan = BeatPlan(
        beats_s=[0.0, 2.0, 4.0],
        downbeats_s=[0.0, 4.0],
        phrase_boundaries_s=[0.0],
        energy_curve=[0.2, 0.9],
        sections=[BeatSection(label="peak", start_s=0.0, end_s=8.0, energy=0.9, cut_density=0.9)],
    )

    plan = build_effect_plan(story, beat_plan)

    assert plan.decisions[1].transition == TransitionType.SMOOTH_ZOOM
    assert plan.decisions[1].confidence >= 0.75


def test_effect_plan_keeps_calm_establishing_as_dissolve() -> None:
    story = StoryPlan(
        target_duration_s=10.0,
        clips=[
            _clip(0, DroneShotType.ESTABLISHING, "establish"),
            _clip(1, DroneShotType.PULL_BACK, "release"),
        ],
    )
    beat_plan = BeatPlan(
        beats_s=[0.0, 2.0],
        downbeats_s=[0.0],
        phrase_boundaries_s=[0.0],
        energy_curve=[0.2],
        sections=[BeatSection(label="calm", start_s=0.0, end_s=8.0, energy=0.2, cut_density=0.35)],
    )

    plan = build_effect_plan(story, beat_plan)

    assert plan.decisions[1].transition == TransitionType.DISSOLVE
```

- [ ] **Step 2: Run failing tests**

```powershell
py -m pytest tests\planning\test_effects.py -q
```

Expected: FAIL because `planning.effects` does not exist.

- [ ] **Step 3: Implement effect planner**

Create `src/aicutting/planning/effects.py`:

```python
from aicutting.core.models import DroneShotType, TransitionType
from aicutting.director.drone_models import BeatPlan, EffectDecision, EffectPlan, StoryPlan


def build_effect_plan(story: StoryPlan, beat_plan: BeatPlan) -> EffectPlan:
    decisions: list[EffectDecision] = []
    energy = _dominant_energy(beat_plan)
    for index, clip in enumerate(story.clips):
        if index == 0:
            transition = TransitionType.HARD_CUT
            duration = 0.0
            confidence = 1.0
            reason = "first clip starts clean"
        else:
            previous = story.clips[index - 1]
            transition, duration, confidence, reason = _transition(previous.shot_type, clip.shot_type, energy)
        decisions.append(
            EffectDecision(
                clip_index=index,
                transition=transition,
                duration_s=duration,
                confidence=confidence,
                beat_anchor_s=clip.beat_anchor_s,
                reason=reason,
            )
        )
    return EffectPlan(decisions=decisions)


def _dominant_energy(beat_plan: BeatPlan) -> float:
    if not beat_plan.sections:
        return 0.2
    return max(section.energy for section in beat_plan.sections)


def _transition(
    previous: DroneShotType,
    current: DroneShotType,
    energy: float,
) -> tuple[TransitionType, float, float, str]:
    if energy >= 0.72 and current in {DroneShotType.APPROACH, DroneShotType.REVEAL, DroneShotType.FLY_THROUGH}:
        return TransitionType.SMOOTH_ZOOM, 0.25, 0.82, "forward/reveal motion on high-energy beat"
    if energy >= 0.78 and previous in {DroneShotType.TRACKING, DroneShotType.ORBIT}:
        return TransitionType.WHIP_BLUR, 0.18, 0.76, "lateral motion supports whip blur"
    if energy <= 0.35 and current in {DroneShotType.PULL_BACK, DroneShotType.ESTABLISHING, DroneShotType.TOP_DOWN}:
        return TransitionType.DISSOLVE, 0.35, 0.8, "calm scenic release"
    if energy >= 0.82:
        return TransitionType.FLASH_CUT, 0.08, 0.7, "high-energy accent"
    return TransitionType.HARD_CUT, 0.0, 0.9, "clean beat cut fallback"
```

- [ ] **Step 4: Run tests and commit**

```powershell
py -m pytest tests\planning\test_effects.py -q
py -m ruff check src\aicutting\planning\effects.py tests\planning\test_effects.py
py -m mypy src
git add src\aicutting\planning\effects.py tests\planning\test_effects.py
git commit -m "feat: choose motion aware drone effects"
```

---

### Task 6: Integrate 2.0 Planning Into Cut Plan

**Files:**
- Modify: `src/aicutting/planning/engine.py`
- Modify: `src/aicutting/planning/transitions.py`
- Test: `tests/planning/test_engine.py`
- Test: `tests/planning/test_transitions.py`

- [ ] **Step 1: Write failing engine integration test**

Add to `tests/planning/test_engine.py`:

```python
def test_build_cut_plan_uses_drone_story_and_effects_for_20_candidates() -> None:
    video = Path("clip.mp4")
    report = AnalysisReport(
        media=[MediaAsset(path=video, duration_s=30, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(asset_path=video, start_s=0, end_s=5, quality_score=0.8, motion_score=0.5, diversity_key="a", shot_type=DroneShotType.ESTABLISHING, drone_director_score=0.8),
            ClipCandidate(asset_path=video, start_s=5, end_s=10, quality_score=0.8, motion_score=0.5, diversity_key="b", shot_type=DroneShotType.APPROACH, drone_director_score=0.82),
            ClipCandidate(asset_path=video, start_s=10, end_s=15, quality_score=0.8, motion_score=0.5, diversity_key="c", shot_type=DroneShotType.REVEAL, drone_director_score=0.95),
            ClipCandidate(asset_path=video, start_s=15, end_s=20, quality_score=0.8, motion_score=0.5, diversity_key="d", shot_type=DroneShotType.PULL_BACK, drone_director_score=0.78),
        ],
        audio=AudioAnalysis(path=None, duration_s=12.0, beats_s=[0, 2, 4, 6, 8], energy=[0.2, 0.9]),
    )

    plan = build_cut_plan(report)

    assert plan.style == "ai_drone_director_20"
    assert any(clip.transition_in.kind == TransitionType.SMOOTH_ZOOM for clip in plan.timeline.clips)
    assert plan.notes[0].startswith("Generated by AI Drone Director 2.0")
```

Add imports:

```python
from aicutting.core.models import DroneShotType, TransitionType
```

- [ ] **Step 2: Run failing test**

```powershell
py -m pytest tests\planning\test_engine.py::test_build_cut_plan_uses_drone_story_and_effects_for_20_candidates -q
```

Expected: FAIL because `build_cut_plan` still returns `adaptive_clean_cinematic`.

- [ ] **Step 3: Modify `build_cut_plan` to use 2.0 when shot types exist**

In `src/aicutting/planning/engine.py`, import:

```python
from aicutting.analysis.beat_plan import build_beat_plan
from aicutting.core.models import DroneShotType
from aicutting.planning.effects import build_effect_plan
from aicutting.planning.story import build_story_plan
```

At the top of `build_cut_plan`, after `target_duration_s`, add:

```python
    if any(candidate.shot_type != DroneShotType.UNKNOWN for candidate in report.candidates):
        return _build_drone_director_20_plan(report, target_duration_s)
```

Add helper:

```python
def _build_drone_director_20_plan(report: AnalysisReport, target_duration_s: float) -> CutPlan:
    beat_plan = build_beat_plan(report.audio)
    story = build_story_plan(report.candidates, beat_plan, target_duration_s)
    effects = build_effect_plan(story, beat_plan)
    base_asset = report.media[0]
    clips: list[TimelineClip] = []
    timeline_cursor = 0.0
    for index, story_clip in enumerate(story.clips):
        decision = effects.decisions[index]
        clip_duration = min(story_clip.source_end_s - story_clip.source_start_s, target_duration_s - timeline_cursor)
        if clip_duration <= 0:
            break
        clips.append(
            TimelineClip(
                asset_path=story_clip.asset_path,
                source_start_s=story_clip.source_start_s,
                source_end_s=story_clip.source_start_s + clip_duration,
                timeline_start_s=round(timeline_cursor, 3),
                transition_in=Transition(kind=decision.transition, duration_s=decision.duration_s),
                speed=1.0,
                color_intent="subtle_cinematic",
            )
        )
        timeline_cursor = round(timeline_cursor + clip_duration, 3)
    return CutPlan(
        target_duration_s=target_duration_s,
        style="ai_drone_director_20",
        timeline=Timeline(target_duration_s=target_duration_s, clips=clips, fps=base_asset.fps, width=base_asset.width, height=base_asset.height),
        notes=["Generated by AI Drone Director 2.0 story, beat, and effect planning."],
    )
```

- [ ] **Step 4: Keep old transition chooser compatible**

No behavior change is required in `src/aicutting/planning/transitions.py` for old plans. Add a regression test to `tests/planning/test_transitions.py`:

```python
def test_legacy_transition_chooser_still_returns_basic_transition() -> None:
    previous = ClipCandidate(asset_path=Path("a.mp4"), start_s=0, end_s=4, quality_score=0.8, motion_score=0.3, diversity_key="a")
    current = ClipCandidate(asset_path=Path("b.mp4"), start_s=0, end_s=4, quality_score=0.8, motion_score=0.32, diversity_key="b")

    transition = choose_transition(previous=previous, current=current, beat_energy=0.2)

    assert transition.kind == TransitionType.DISSOLVE
```

- [ ] **Step 5: Run tests and commit**

```powershell
py -m pytest tests\planning\test_engine.py tests\planning\test_transitions.py -q
py -m ruff check src\aicutting\planning\engine.py src\aicutting\planning\transitions.py tests\planning\test_engine.py tests\planning\test_transitions.py
py -m mypy src
git add src\aicutting\planning\engine.py src\aicutting\planning\transitions.py tests\planning\test_engine.py tests\planning\test_transitions.py
git commit -m "feat: integrate ai drone director planning"
```

---

### Task 7: Write 2.0 Artifacts From Pipeline

**Files:**
- Modify: `src/aicutting/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing pipeline artifact test**

Add to `tests/test_pipeline.py`:

```python
def test_pipeline_writes_drone_director_20_artifacts(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")
    report = AnalysisReport(
        media=[MediaAsset(path=video, duration_s=20, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(
                asset_path=video,
                start_s=2,
                end_s=7,
                quality_score=0.9,
                motion_score=0.7,
                diversity_key="clip:0",
                shot_type=DroneShotType.REVEAL,
                drone_director_score=0.9,
                reveal_score=0.85,
                novelty_score=0.7,
                technical_score=0.8,
                motion_intent_score=0.9,
            )
        ],
        audio=AudioAnalysis(path=None, duration_s=8.0, beats_s=[0, 2, 4, 6], energy=[0.2, 0.8]),
    )
    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: report,
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )

    CutPipeline(dependencies=deps).cut(input_dir, None, output_dir, dry_run=True)

    assert (output_dir / "shot-candidates.json").exists()
    assert (output_dir / "beat-plan.json").exists()
    assert (output_dir / "story-plan.json").exists()
    assert (output_dir / "effect-plan.json").exists()
    assert (output_dir / "director-2-report.json").exists()
```

Add import:

```python
from aicutting.core.models import DroneShotType
```

- [ ] **Step 2: Run failing test**

```powershell
py -m pytest tests\test_pipeline.py::test_pipeline_writes_drone_director_20_artifacts -q
```

Expected: FAIL because the files are not written.

- [ ] **Step 3: Implement artifact helpers in `pipeline.py`**

Import:

```python
from aicutting.analysis.beat_plan import build_beat_plan
from aicutting.core.models import DroneShotType
from aicutting.director.drone_models import Director2Report, ShotCandidateArtifact
from aicutting.planning.effects import build_effect_plan
from aicutting.planning.story import build_story_plan
```

Before `emit_progress(progress, PipelinePhase.EXPORTING_RESOLVE_HANDOFF...)`, add:

```python
        if any(candidate.shot_type != DroneShotType.UNKNOWN for candidate in director_outputs.analysis.candidates):
            beat_plan = build_beat_plan(report.audio)
            story_plan = build_story_plan(director_outputs.analysis.candidates, beat_plan, plan.target_duration_s)
            effect_plan = build_effect_plan(story_plan, beat_plan)
            shot_artifacts = [_shot_candidate_artifact(candidate) for candidate in report.candidates]
            selected_count = sum(1 for item in shot_artifacts if item.selected)
            rejected_count = sum(1 for item in shot_artifacts if item.rejected)
            average_score = (
                round(sum(item.drone_director_score for item in shot_artifacts) / len(shot_artifacts), 6)
                if shot_artifacts
                else 0.0
            )
            write_json_models(output_dir / "shot-candidates.json", shot_artifacts)
            write_json_model(output_dir / "beat-plan.json", beat_plan)
            write_json_model(output_dir / "story-plan.json", story_plan)
            write_json_model(output_dir / "effect-plan.json", effect_plan)
            write_json_model(
                output_dir / "director-2-report.json",
                Director2Report(
                    selected_count=selected_count,
                    rejected_count=rejected_count,
                    average_drone_director_score=average_score,
                    warnings=[],
                ),
            )
```

Add helper at bottom:

```python
def _shot_candidate_artifact(candidate: ClipCandidate) -> ShotCandidateArtifact:
    selected = candidate.rejection_reason is None
    return ShotCandidateArtifact(
        asset_path=candidate.asset_path,
        start_s=candidate.start_s,
        end_s=candidate.end_s,
        shot_type=candidate.shot_type,
        selected=selected,
        rejected=not selected,
        rejection_reason=candidate.rejection_reason,
        technical_score=candidate.technical_score or candidate.quality_score,
        stability_score=candidate.smoothness_score or 0.0,
        composition_score=candidate.composition_score or 0.0,
        motion_intent_score=candidate.motion_intent_score or candidate.motion_score,
        reveal_score=candidate.reveal_score or 0.0,
        novelty_score=candidate.novelty_score or 0.0,
        drone_director_score=candidate.director_score,
        reasons=[
            f"{candidate.shot_type.value} score {candidate.director_score:.2f}",
            candidate.rejection_reason or "selected",
        ],
    )
```

- [ ] **Step 4: Run tests and commit**

```powershell
py -m pytest tests\test_pipeline.py -q
py -m ruff check src\aicutting\pipeline.py tests\test_pipeline.py
py -m mypy src
git add src\aicutting\pipeline.py tests\test_pipeline.py
git commit -m "feat: write ai drone director artifacts"
```

---

### Task 8: Render Effect Fallbacks In FFmpeg

**Files:**
- Modify: `src/aicutting/render/ffmpeg.py`
- Test: `tests/render/test_ffmpeg.py`

- [ ] **Step 1: Write failing render command tests**

Add to `tests/render/test_ffmpeg.py`:

```python
def test_build_ffmpeg_command_renders_smooth_zoom_as_filter() -> None:
    timeline = _timeline().model_copy(
        update={
            "clips": [
                _timeline().clips[0],
                _timeline().clips[0].model_copy(
                    update={
                        "asset_path": Path("clip-b.mp4"),
                        "timeline_start_s": 4.0,
                        "transition_in": Transition(kind=TransitionType.SMOOTH_ZOOM, duration_s=0.25),
                    }
                ),
            ]
        }
    )

    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "zoompan" in filter_complex or "xfade" in filter_complex
```

- [ ] **Step 2: Run failing test**

```powershell
py -m pytest tests\render\test_ffmpeg.py::test_build_ffmpeg_command_renders_smooth_zoom_as_filter -q
```

Expected: FAIL because smooth zoom currently falls through to concat/xfade behavior without explicit support.

- [ ] **Step 3: Implement stable fallback**

In `src/aicutting/render/ffmpeg.py`, keep rendering simple for 2.0:

- `SMOOTH_ZOOM`: use `xfade=transition=fade` for now and add `zoompan` only to the incoming clip filter when stable.
- `WHIP_BLUR`: use `xfade=transition=fadeblack` when available or fall back to hard concat.
- `FLASH_CUT`: use a very short fade or hard cut.
- `SPEED_RAMP`: this implementation records the decision but renders it as a hard-cut fallback until timeline-level speed curves exist.
- `MATCH_MOTION`: use hard cut unless dissolve confidence is encoded elsewhere.

Minimal code change: update the dissolve branch condition in `_compose_video_filter`:

```python
        if clip.transition_in.kind in {
            TransitionType.DISSOLVE,
            TransitionType.SMOOTH_ZOOM,
            TransitionType.WHIP_BLUR,
        } and clip.transition_in.duration_s > 0:
            transition_name = _xfade_transition_name(clip.transition_in.kind)
```

Add:

```python
def _xfade_transition_name(kind: TransitionType) -> str:
    if kind == TransitionType.WHIP_BLUR:
        return "fadeblack"
    return "fade"
```

Use `transition={transition_name}` in the xfade string.

- [ ] **Step 4: Run tests and commit**

```powershell
py -m pytest tests\render\test_ffmpeg.py -q
py -m ruff check src\aicutting\render\ffmpeg.py tests\render\test_ffmpeg.py
py -m mypy src
git add src\aicutting\render\ffmpeg.py tests\render\test_ffmpeg.py
git commit -m "feat: render drone director effect fallbacks"
```

---

### Task 9: Full Pipeline Verification And Docs

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Test: full suite

- [ ] **Step 1: Update README 2.0 status**

Add a short section to `README.md` under `Current Status`:

```markdown
### AI Drone Director 2.0

The 2.0 director path is drone-only. It adds richer drone shot classification,
beat planning, story arc planning, motion-aware effect decisions, and review
artifacts. It is designed to improve raw-moment selection before adding visual
effects.
```

- [ ] **Step 2: Update quickstart outputs**

In `docs/quickstart.md`, add to "Typical output files":

```markdown
- `shot-candidates.json`: drone shot types, scores, and rejection reasons.
- `beat-plan.json`: beat targets, energy sections, and cut density.
- `story-plan.json`: selected edit arc.
- `effect-plan.json`: transition and animation choices.
- `director-2-report.json`: summary metrics for AI Drone Director 2.0.
```

- [ ] **Step 3: Run full verification**

Run:

```powershell
py -m pytest -q
py -m ruff check .
py -m mypy src
```

Expected:

- all tests pass,
- Ruff reports all checks passed,
- MyPy reports success.

- [ ] **Step 4: Commit docs**

```powershell
git add README.md docs\quickstart.md
git commit -m "docs: document ai drone director 2.0"
```

---

## Plan Self-Review

Spec coverage:

- Raw drone moment intelligence: Tasks 1, 2, 4, 7.
- Beat-aware planning: Tasks 3, 4, 6, 7.
- Motion-aware transitions: Tasks 1, 5, 6, 8.
- Auditable artifacts: Tasks 1, 7, 9.
- Preserve deterministic local behavior: all tasks use deterministic analysis and existing local pipeline.

Placeholder scan:

- No `TBD`, `TODO`, or "fill in later" placeholders.
- Each task names files, tests, commands, and expected outcomes.

Type consistency:

- `DroneShotType`, `BeatPlan`, `StoryPlan`, `EffectPlan`, and `TransitionType` names are introduced before later tasks use them.
- `ClipCandidate.shot_type` and `ClipCandidate.drone_director_score` are added before planning uses them.
