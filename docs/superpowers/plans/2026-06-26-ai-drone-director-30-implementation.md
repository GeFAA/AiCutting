# AI Drone Director 3.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken 4-clip 2.0 story arc with a full-length, beat-driven edit whose creative judgment (rate footage, reject takeoff/landing/boring, select + order, place effects) is made by the local vision agent (codex, fallback claude), with deterministic beat timing, assembly, and real FFmpeg effect rendering, plus a deterministic offline fallback.

**Architecture:** `videos → keyframes/contact-sheets (det.)` and `music → beat grid (det.)`; the agent rates the contact sheets and then designs the ordered edit; deterministic code assembles the edit onto the beat grid and renders real effects; a deterministic editor is the no-agent fallback. Extends the existing codex/claude plumbing (`agents/backends.py`, `analysis/screenshots.py`, the `exec --image --output-schema` pattern in `director/location.py`).

**Tech Stack:** Python 3.11+, Pydantic, OpenCV, NumPy, librosa, FFmpeg, codex/claude CLIs, pytest, ruff, mypy.

## Global Constraints

- Python 3.11+; ruff + mypy (strict) clean; line length 100.
- Git author is `GeFAA <121340757+GeFAA@users.noreply.github.com>`; do NOT add `Co-Authored-By` trailers.
- Tests must not call real codex/claude or real FFmpeg except the explicit Task 9 real-footage run; mock the agent `runner` (like `tests/director/test_location.py`) and use synthetic frames.
- Agent calls are bounded: `MAX_CONTACT_SHEETS` total rating calls + 1 edit call. Cache agent responses to disk.
- Deterministic stages stay deterministic; the agent stages are the only non-deterministic ones, behind a fallback.
- New 3.0 path is selected for drone material; the legacy non-drone path is untouched.

---

## File Structure

- Create `src/aicutting/director/edit_models.py` — 3.0 Pydantic models: `FootageMoment`, `ContactSheet`, `MomentRating`, `RhythmSlot`, `EditClip`, `EditDecision`, `Director3Report`.
- Modify `src/aicutting/analysis/screenshots.py` — add deterministic moment sampling (with takeoff/landing trim) and contact-sheet tiling.
- Create `src/aicutting/planning/rhythm.py` — deterministic beat/energy cut grid.
- Create `src/aicutting/director/edit_agent.py` — agent rating + edit-decision calls (codex/claude), schemas, prompts, parsing; mirrors `director/location.py`.
- Create `src/aicutting/planning/assemble.py` — deterministic assembly of an `EditDecision` onto the grid into a `CutPlan`, plus the deterministic fallback editor.
- Modify `src/aicutting/planning/engine.py` — route drone material to the 3.0 assembler.
- Modify `src/aicutting/render/ffmpeg.py` — real effect rendering (xfade catalogue, zoompan push-in, speed accent) with per-effect fallback.
- Modify `src/aicutting/pipeline.py` — wire contact sheets → ratings → grid → edit → assemble → render; write artifacts; fallback.
- Modify `README.md` / `docs/quickstart.md` — document 3.0 and its agent dependency.

---

### Task 1: 3.0 models

**Files:**
- Create: `src/aicutting/director/edit_models.py`
- Test: `tests/director/test_edit_models.py`

**Interfaces:**
- Produces: `FootageMoment(moment_id:str, asset_path:Path, timestamp_s:float)`, `ContactSheet(path:Path, moment_ids:list[str])`, `MomentRating(moment_id:str, cinematic_score:float, shot_type:DroneShotType, keep:bool, reason:str)`, `RhythmSlot(index:int, start_s:float, end_s:float, energy:float, is_accent:bool, section:str)` with `.duration_s`, `EditClip(slot_index:int, moment_id:str, effect:TransitionType, reason:str)`, `EditDecision(arc:str, clips:list[EditClip])`, `Director3Report(used_agent:bool, backend:str|None, rated_moments:int, kept_moments:int, timeline_clips:int, warnings:list[str])`.

- [ ] **Step 1: Write the failing test**

Create `tests/director/test_edit_models.py`:

```python
from pathlib import Path

from aicutting.core.models import DroneShotType, TransitionType
from aicutting.director.edit_models import (
    ContactSheet,
    EditClip,
    EditDecision,
    FootageMoment,
    MomentRating,
    RhythmSlot,
)


def test_rhythm_slot_exposes_duration() -> None:
    slot = RhythmSlot(index=0, start_s=2.0, end_s=5.0, energy=0.8, is_accent=True, section="peak")
    assert slot.duration_s == 3.0


def test_edit_decision_round_trips() -> None:
    moment = FootageMoment(moment_id="m001", asset_path=Path("a.mp4"), timestamp_s=12.0)
    sheet = ContactSheet(path=Path("sheet-1.jpg"), moment_ids=["m001"])
    rating = MomentRating(
        moment_id="m001",
        cinematic_score=0.9,
        shot_type=DroneShotType.REVEAL,
        keep=True,
        reason="strong reveal",
    )
    decision = EditDecision(
        arc="calm build to reveal",
        clips=[EditClip(slot_index=0, moment_id="m001", effect=TransitionType.SMOOTH_ZOOM, reason="peak")],
    )

    assert moment.moment_id == "m001"
    assert sheet.moment_ids == ["m001"]
    assert rating.keep is True
    assert decision.clips[0].effect == TransitionType.SMOOTH_ZOOM
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/director/test_edit_models.py -q`
Expected: FAIL (`No module named 'aicutting.director.edit_models'`).

- [ ] **Step 3: Write the implementation**

Create `src/aicutting/director/edit_models.py`:

```python
from pathlib import Path

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from aicutting.core.models import DroneShotType, TransitionType


class FootageMoment(BaseModel):
    moment_id: str
    asset_path: Path
    timestamp_s: float = Field(ge=0)


class ContactSheet(BaseModel):
    path: Path
    moment_ids: list[str]


class MomentRating(BaseModel):
    moment_id: str
    cinematic_score: float = Field(ge=0, le=1)
    shot_type: DroneShotType
    keep: bool
    reason: str


class RhythmSlot(BaseModel):
    index: int = Field(ge=0)
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    energy: float = Field(ge=0, le=1)
    is_accent: bool
    section: str

    @field_validator("end_s")
    @classmethod
    def end_after_start(cls, value: float, info: ValidationInfo) -> float:
        if value <= info.data.get("start_s", 0.0):
            raise ValueError("end_s must be greater than start_s")
        return value

    @property
    def duration_s(self) -> float:
        return round(self.end_s - self.start_s, 6)


class EditClip(BaseModel):
    slot_index: int = Field(ge=0)
    moment_id: str
    effect: TransitionType
    reason: str


class EditDecision(BaseModel):
    arc: str
    clips: list[EditClip]


class Director3Report(BaseModel):
    used_agent: bool
    backend: str | None
    rated_moments: int = Field(ge=0)
    kept_moments: int = Field(ge=0)
    timeline_clips: int = Field(ge=0)
    warnings: list[str]
```

- [ ] **Step 4: Run, lint, type-check, commit**

```powershell
py -m pytest tests/director/test_edit_models.py -q
py -m ruff check src/aicutting/director/edit_models.py tests/director/test_edit_models.py
py -m mypy src
git add src/aicutting/director/edit_models.py tests/director/test_edit_models.py
git commit -m "feat: add drone director 3.0 models"
```

Expected: PASS, ruff clean, mypy clean.

---

### Task 2: Contact-sheet sampling (deterministic)

**Files:**
- Modify: `src/aicutting/analysis/screenshots.py`
- Test: `tests/analysis/test_screenshots.py`

**Interfaces:**
- Consumes: `MediaAsset` (`path`, `duration_s`), `FootageMoment`, `ContactSheet`.
- Produces: `sample_footage_moments(media:list[MediaAsset], trim_s:float=12.0, stride_s:float=4.0, max_moments:int=48) -> list[FootageMoment]`; `build_contact_sheets(moments:list[FootageMoment], output_dir:Path, per_sheet:int=12, columns:int=4, thumb_w:int=320) -> list[ContactSheet]`.

- [ ] **Step 1: Write the failing test**

Create `tests/analysis/test_screenshots.py`:

```python
from pathlib import Path

import numpy as np

from aicutting.analysis.screenshots import build_contact_sheets, sample_footage_moments
from aicutting.core.models import MediaAsset


def test_sample_skips_takeoff_and_landing_zones() -> None:
    asset = MediaAsset(path=Path("flight.mp4"), duration_s=60.0, width=1920, height=1080, fps=25.0)

    moments = sample_footage_moments([asset], trim_s=12.0, stride_s=4.0, max_moments=48)

    assert moments, "expected sampled moments"
    assert all(12.0 <= m.timestamp_s <= 48.0 for m in moments)
    assert len({m.moment_id for m in moments}) == len(moments)


def test_build_contact_sheets_tiles_moments(monkeypatch, tmp_path: Path) -> None:
    asset = MediaAsset(path=tmp_path / "flight.mp4", duration_s=60.0, width=1920, height=1080, fps=25.0)
    (tmp_path / "flight.mp4").write_text("", encoding="utf-8")
    moments = sample_footage_moments([asset], trim_s=12.0, stride_s=8.0, max_moments=6)

    class FakeCapture:
        def isOpened(self) -> bool:
            return True

        def set(self, prop: int, value: float) -> None:
            del prop, value

        def read(self):
            return True, np.full((1080, 1920, 3), 128, dtype=np.uint8)

        def release(self) -> None:
            pass

    monkeypatch.setattr("aicutting.analysis.screenshots.cv2.VideoCapture", lambda _: FakeCapture())

    sheets = build_contact_sheets(moments, tmp_path / "sheets", per_sheet=4, columns=2)

    assert sheets, "expected contact sheets"
    assert sheets[0].path.exists()
    covered = [mid for sheet in sheets for mid in sheet.moment_ids]
    assert covered == [m.moment_id for m in moments]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/analysis/test_screenshots.py -q`
Expected: FAIL (`cannot import name 'sample_footage_moments'`).

- [ ] **Step 3: Write the implementation**

Append to `src/aicutting/analysis/screenshots.py` (keep `extract_location_keyframes`; add imports `numpy as np`, `MediaAsset`, `ContactSheet`, `FootageMoment`):

```python
def sample_footage_moments(
    media: list[MediaAsset],
    trim_s: float = 12.0,
    stride_s: float = 4.0,
    max_moments: int = 48,
) -> list[FootageMoment]:
    moments: list[FootageMoment] = []
    for asset in media:
        usable = asset.duration_s - 2 * trim_s
        start = trim_s
        if usable <= stride_s:  # short clip: proportional 10% trim
            edge = max(0.0, asset.duration_s * 0.1)
            start = edge
            end = asset.duration_s - edge
        else:
            end = asset.duration_s - trim_s
        cursor = start
        while cursor <= end and len(moments) < max_moments:
            moments.append(
                FootageMoment(
                    moment_id=f"m{len(moments) + 1:03d}",
                    asset_path=asset.path,
                    timestamp_s=round(cursor, 3),
                )
            )
            cursor += stride_s
    return moments


def build_contact_sheets(
    moments: list[FootageMoment],
    output_dir: Path,
    per_sheet: int = 12,
    columns: int = 4,
    thumb_w: int = 320,
) -> list[ContactSheet]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sheets: list[ContactSheet] = []
    for chunk_start in range(0, len(moments), per_sheet):
        chunk = moments[chunk_start : chunk_start + per_sheet]
        tiles, ids = _render_tiles(chunk, thumb_w)
        if not tiles:
            continue
        sheet_image = _tile_grid(tiles, columns)
        sheet_path = output_dir / f"contact-sheet-{len(sheets) + 1:02d}.jpg"
        cv2.imwrite(str(sheet_path), sheet_image)
        sheets.append(ContactSheet(path=sheet_path, moment_ids=ids))
    return sheets


def _render_tiles(chunk: list[FootageMoment], thumb_w: int) -> tuple[list[np.ndarray], list[str]]:
    tiles: list[np.ndarray] = []
    ids: list[str] = []
    by_asset: dict[Path, list[FootageMoment]] = {}
    for moment in chunk:
        by_asset.setdefault(moment.asset_path, []).append(moment)
    ordered = {m.moment_id: None for m in chunk}
    rendered: dict[str, np.ndarray] = {}
    for asset_path, items in by_asset.items():
        capture = cv2.VideoCapture(str(asset_path))
        try:
            if not capture.isOpened():
                continue
            for moment in items:
                capture.set(cv2.CAP_PROP_POS_MSEC, moment.timestamp_s * 1000.0)
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue
                rendered[moment.moment_id] = _label_thumb(frame, moment, thumb_w)
        finally:
            capture.release()
    for moment_id in ordered:
        if moment_id in rendered:
            tiles.append(rendered[moment_id])
            ids.append(moment_id)
    return tiles, ids


def _label_thumb(frame: np.ndarray, moment: FootageMoment, thumb_w: int) -> np.ndarray:
    height, width = frame.shape[:2]
    thumb_h = max(1, int(height * (thumb_w / max(1, width))))
    thumb = cv2.resize(frame, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
    label = f"{moment.moment_id} {moment.asset_path.stem} {moment.timestamp_s:.0f}s"
    cv2.rectangle(thumb, (0, 0), (thumb_w, 22), (0, 0, 0), -1)
    cv2.putText(thumb, label, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    return thumb


def _tile_grid(tiles: list[np.ndarray], columns: int) -> np.ndarray:
    thumb_h = max(t.shape[0] for t in tiles)
    thumb_w = max(t.shape[1] for t in tiles)
    blank = np.zeros((thumb_h, thumb_w, 3), dtype=np.uint8)
    padded = [
        t if t.shape[:2] == (thumb_h, thumb_w) else cv2.resize(t, (thumb_w, thumb_h))
        for t in tiles
    ]
    rows: list[np.ndarray] = []
    for row_start in range(0, len(padded), columns):
        row = padded[row_start : row_start + columns]
        while len(row) < columns:
            row.append(blank)
        rows.append(np.hstack(row))
    return np.vstack(rows)
```

- [ ] **Step 4: Run, lint, type-check, commit**

```powershell
py -m pytest tests/analysis/test_screenshots.py -q
py -m ruff check src/aicutting/analysis/screenshots.py tests/analysis/test_screenshots.py
py -m mypy src
git add src/aicutting/analysis/screenshots.py tests/analysis/test_screenshots.py
git commit -m "feat: sample footage into contact sheets"
```

Expected: PASS, ruff clean, mypy clean.

---

### Task 3: Beat/energy rhythm grid (deterministic)

**Files:**
- Create: `src/aicutting/planning/rhythm.py`
- Test: `tests/planning/test_rhythm.py`

**Interfaces:**
- Consumes: `BeatPlan` (`beats_s`, `downbeats_s`, `energy_curve`, `sections`), `RhythmSlot`.
- Produces: `build_rhythm_grid(beat_plan:BeatPlan, target_duration_s:float) -> list[RhythmSlot]`.

- [ ] **Step 1: Write the failing test**

Create `tests/planning/test_rhythm.py`:

```python
from aicutting.analysis.beat_plan import build_beat_plan
from aicutting.core.models import AudioAnalysis
from aicutting.director.edit_models import RhythmSlot
from aicutting.planning.rhythm import build_rhythm_grid


def test_grid_fills_target_and_snaps_to_beats() -> None:
    beats = [i * 0.5 for i in range(0, 60)]  # 30 s of beats
    audio = AudioAnalysis(path=None, duration_s=30.0, beats_s=beats, energy=[0.2, 0.9, 0.3])
    grid = build_rhythm_grid(build_beat_plan(audio), target_duration_s=30.0)

    assert grid, "expected slots"
    assert grid[0].start_s == 0.0
    assert grid[-1].end_s <= 30.0 + 0.5
    assert grid[-1].end_s >= 24.0  # fills most of the song
    assert all(b.start_s < b.end_s for b in grid)
    assert all(grid[i].end_s == grid[i + 1].start_s for i in range(len(grid) - 1))


def test_high_energy_slots_are_shorter_than_calm_slots() -> None:
    beats = [i * 0.5 for i in range(0, 80)]
    calm = AudioAnalysis(path=None, duration_s=40.0, beats_s=beats, energy=[0.1])
    loud = AudioAnalysis(path=None, duration_s=40.0, beats_s=beats, energy=[0.95])
    calm_grid = build_rhythm_grid(build_beat_plan(calm), target_duration_s=40.0)
    loud_grid = build_rhythm_grid(build_beat_plan(loud), target_duration_s=40.0)

    assert len(loud_grid) > len(calm_grid)


def test_no_music_uses_default_visual_grid() -> None:
    audio = AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[])
    grid = build_rhythm_grid(build_beat_plan(audio), target_duration_s=12.0)

    assert grid[0].start_s == 0.0
    assert grid[-1].end_s <= 12.0
    assert all(2.0 <= b.duration_s <= 3.0 for b in grid)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/planning/test_rhythm.py -q`
Expected: FAIL (`No module named 'aicutting.planning.rhythm'`).

- [ ] **Step 3: Write the implementation**

Create `src/aicutting/planning/rhythm.py`:

```python
from aicutting.director.drone_models import BeatPlan
from aicutting.director.edit_models import RhythmSlot

_DEFAULT_SLOT_S = 2.5


def build_rhythm_grid(beat_plan: BeatPlan, target_duration_s: float) -> list[RhythmSlot]:
    if not beat_plan.beats_s:
        return _visual_grid(target_duration_s)

    beats = [b for b in beat_plan.beats_s if b < target_duration_s]
    if len(beats) < 2:
        return _visual_grid(target_duration_s)
    beats.append(min(target_duration_s, beats[-1] + (beats[-1] - beats[-2])))

    slots: list[RhythmSlot] = []
    i = 0
    while i < len(beats) - 1:
        start = beats[i]
        energy = _energy_at(beat_plan, start, target_duration_s)
        span = 1 if energy >= 0.72 else 2 if energy >= 0.45 else 3
        j = min(i + span, len(beats) - 1)
        end = beats[j]
        if end <= start:
            break
        slots.append(
            RhythmSlot(
                index=len(slots),
                start_s=round(start, 3),
                end_s=round(end, 3),
                energy=round(energy, 6),
                is_accent=energy >= 0.72,
                section=_section_at(beat_plan, start),
            )
        )
        i = j
    return slots or _visual_grid(target_duration_s)


def _visual_grid(target_duration_s: float) -> list[RhythmSlot]:
    slots: list[RhythmSlot] = []
    cursor = 0.0
    while cursor + 0.5 < target_duration_s:
        end = min(cursor + _DEFAULT_SLOT_S, target_duration_s)
        if end - cursor < 1.0:
            break
        slots.append(
            RhythmSlot(
                index=len(slots),
                start_s=round(cursor, 3),
                end_s=round(end, 3),
                energy=0.4,
                is_accent=False,
                section="visual_default",
            )
        )
        cursor = end
    return slots


def _energy_at(beat_plan: BeatPlan, time_s: float, total_s: float) -> float:
    curve = beat_plan.energy_curve
    if not curve or total_s <= 0:
        return 0.4
    ratio = max(0.0, min(1.0, time_s / total_s))
    index = min(len(curve) - 1, int(round(ratio * (len(curve) - 1))))
    return float(curve[index])


def _section_at(beat_plan: BeatPlan, time_s: float) -> str:
    for section in beat_plan.sections:
        if section.start_s <= time_s < section.end_s:
            return section.label
    return beat_plan.sections[0].label if beat_plan.sections else "steady"
```

- [ ] **Step 4: Run, lint, type-check, commit**

```powershell
py -m pytest tests/planning/test_rhythm.py -q
py -m ruff check src/aicutting/planning/rhythm.py tests/planning/test_rhythm.py
py -m mypy src
git add src/aicutting/planning/rhythm.py tests/planning/test_rhythm.py
git commit -m "feat: build beat-energy rhythm grid"
```

Expected: PASS, ruff clean, mypy clean.

---

### Task 4: Agent footage rating

**Files:**
- Create: `src/aicutting/director/edit_agent.py`
- Test: `tests/director/test_edit_agent.py`

**Interfaces:**
- Consumes: `ContactSheet`, `AgentBackend`, `MomentRating`, the `AgentRunner` type from `director/location.py`.
- Produces: `rating_schema() -> dict[str, Any]`; `build_rating_prompt(moment_ids:list[str]) -> str`; `parse_ratings_response(raw:str) -> list[MomentRating]`; `rate_moments(sheets:list[ContactSheet], backends:list[AgentBackend], workdir:Path, runner:AgentRunner=subprocess.run) -> list[MomentRating]`.

- [ ] **Step 1: Write the failing test**

Create `tests/director/test_edit_agent.py`:

```python
import json
import subprocess
from pathlib import Path
from typing import Any

from aicutting.agents.backends import AgentBackend
from aicutting.director.edit_agent import (
    parse_ratings_response,
    rate_moments,
    rating_schema,
)
from aicutting.director.edit_models import ContactSheet


def test_rating_schema_requires_safe_fields() -> None:
    schema = rating_schema()
    item = schema["properties"]["ratings"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == {"moment_id", "cinematic_score", "shot_type", "keep", "reason"}


def test_parse_ratings_accepts_fenced_json() -> None:
    raw = """```json
    {"ratings": [
      {"moment_id": "m001", "cinematic_score": 0.9, "shot_type": "reveal", "keep": true, "reason": "ok"},
      {"moment_id": "m002", "cinematic_score": 0.1, "shot_type": "takeoff_or_landing", "keep": false, "reason": "landing"}
    ]}
    ```"""
    ratings = parse_ratings_response(raw)
    assert [r.moment_id for r in ratings] == ["m001", "m002"]
    assert ratings[1].keep is False


def test_rate_moments_calls_codex_per_sheet(tmp_path: Path) -> None:
    sheet = tmp_path / "contact-sheet-01.jpg"
    sheet.write_bytes(b"img")
    calls: list[list[str]] = []

    def fake_runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        out = Path(command[command.index("--output-last-message") + 1])
        out.write_text(
            json.dumps({"ratings": [
                {"moment_id": "m001", "cinematic_score": 0.8, "shot_type": "approach", "keep": True, "reason": "ok"}
            ]}),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    ratings = rate_moments(
        [ContactSheet(path=sheet, moment_ids=["m001"])],
        [AgentBackend(name="codex", executable="codex", available=True)],
        workdir=tmp_path,
        runner=fake_runner,
    )

    assert ratings[0].moment_id == "m001"
    assert "--image" in calls[0]
    assert str(sheet) in calls[0]


def test_rate_moments_without_backend_returns_empty(tmp_path: Path) -> None:
    sheet = tmp_path / "s.jpg"
    sheet.write_bytes(b"img")
    ratings = rate_moments(
        [ContactSheet(path=sheet, moment_ids=["m001"])],
        [AgentBackend(name="codex", executable=None, available=False)],
        workdir=tmp_path,
    )
    assert ratings == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/director/test_edit_agent.py -q`
Expected: FAIL (`No module named 'aicutting.director.edit_agent'`).

- [ ] **Step 3: Write the implementation**

Create `src/aicutting/director/edit_agent.py` (reuse the helpers in `director/location.py`: `_candidate_json_payloads`, `_preferred_available_backends`, `_backend_executable`, `_raise_for_agent_failure`, `AgentRunner`):

```python
import json
import subprocess
from pathlib import Path
from typing import Any

from aicutting.agents.backends import AgentBackend
from aicutting.core.models import DroneShotType
from aicutting.director.edit_models import ContactSheet, MomentRating
from aicutting.director.location import (
    AgentRunner,
    _backend_executable,
    _candidate_json_payloads,
    _preferred_available_backends,
    _raise_for_agent_failure,
)

_SHOT_TYPES = [member.value for member in DroneShotType]


def rating_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["ratings"],
        "properties": {
            "ratings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["moment_id", "cinematic_score", "shot_type", "keep", "reason"],
                    "properties": {
                        "moment_id": {"type": "string"},
                        "cinematic_score": {"type": "number", "minimum": 0, "maximum": 1},
                        "shot_type": {"type": "string", "enum": _SHOT_TYPES},
                        "keep": {"type": "boolean"},
                        "reason": {"type": "string"},
                    },
                },
            }
        },
    }


def build_rating_prompt(moment_ids: list[str]) -> str:
    ids = ", ".join(moment_ids)
    return (
        "You are a professional drone-video editor. The attached contact sheet shows numbered "
        "frames, each labelled with its moment id (top-left).\n"
        f"Rate ONLY these moments: {ids}.\n"
        "For each: cinematic_score 0-1 (composition, light, interest), the drone shot_type, and "
        "keep=false for takeoff, landing, search/hunting motion, shaky, blurry, or boring sky/ground "
        "with no subject. Be strict: a clean professional edit needs only the best moments.\n"
        "Return JSON only matching the schema."
    )


def parse_ratings_response(raw: str) -> list[MomentRating]:
    for candidate in _candidate_json_payloads(raw):
        try:
            payload = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        ratings = _ratings_from_payload(payload)
        if ratings is not None:
            return ratings
    return []


def _ratings_from_payload(payload: Any) -> list[MomentRating] | None:
    if isinstance(payload, dict) and isinstance(payload.get("result"), str):
        return parse_ratings_response(payload["result"])
    items = payload.get("ratings") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return None
    out: list[MomentRating] = []
    for item in items:
        try:
            out.append(MomentRating.model_validate(item))
        except (TypeError, ValueError):
            continue
    return out


def rate_moments(
    sheets: list[ContactSheet],
    backends: list[AgentBackend],
    workdir: Path,
    runner: AgentRunner = subprocess.run,
) -> list[MomentRating]:
    available = _preferred_available_backends(backends)
    if not available or not sheets:
        return []
    backend = available[0]
    workdir.mkdir(parents=True, exist_ok=True)
    schema_path = workdir / "edit-rating-schema.json"
    schema_path.write_text(json.dumps(rating_schema(), indent=2), encoding="utf-8")
    ratings: list[MomentRating] = []
    for index, sheet in enumerate(sheets, start=1):
        try:
            ratings.extend(_rate_one(backend, sheet, schema_path, workdir, index, runner))
        except Exception:  # noqa: BLE001 - one bad sheet must not abort the batch
            continue
    return ratings


def _rate_one(
    backend: AgentBackend,
    sheet: ContactSheet,
    schema_path: Path,
    workdir: Path,
    index: int,
    runner: AgentRunner,
) -> list[MomentRating]:
    response_path = workdir / f"edit-rating-{index:02d}.json"
    if backend.name == "claude":
        command = [
            _backend_executable(backend), "-p", "--output-format", "json",
            "--json-schema", json.dumps(rating_schema(), ensure_ascii=True),
            "--image", str(sheet.path), build_rating_prompt(sheet.moment_ids),
        ]
    else:
        command = [
            _backend_executable(backend), "exec", "--skip-git-repo-check", "-s", "read-only",
            "--output-schema", str(schema_path), "--output-last-message", str(response_path),
            "--image", str(sheet.path), "-",
        ]
    completed = runner(
        command,
        cwd=str(workdir),
        input=build_rating_prompt(sheet.moment_ids) if backend.name == "codex" else None,
        text=True, capture_output=True, encoding="utf-8", errors="replace",
        check=False, timeout=180,
    )
    _raise_for_agent_failure(completed)
    raw = response_path.read_text(encoding="utf-8") if response_path.exists() else completed.stdout
    return parse_ratings_response(raw)
```

- [ ] **Step 4: Run, lint, type-check, commit**

```powershell
py -m pytest tests/director/test_edit_agent.py -q
py -m ruff check src/aicutting/director/edit_agent.py tests/director/test_edit_agent.py
py -m mypy src
git add src/aicutting/director/edit_agent.py tests/director/test_edit_agent.py
git commit -m "feat: rate footage moments with the vision agent"
```

Expected: PASS, ruff clean, mypy clean. (If ruff flags the `_`-prefixed imports as private, add `# noqa: PLC2701` or re-export them from `location.py`; prefer re-export by adding them to a small public surface if needed.)

---

### Task 5: Agent edit decision

**Files:**
- Modify: `src/aicutting/director/edit_agent.py`
- Test: `tests/director/test_edit_agent.py`

**Interfaces:**
- Consumes: `MomentRating`, `RhythmSlot`, `AgentBackend`, `TransitionType`, `EditDecision`, `EditClip`.
- Produces: `edit_schema() -> dict[str, Any]`; `build_edit_prompt(kept:list[MomentRating], slots:list[RhythmSlot]) -> str`; `parse_edit_response(raw:str) -> EditDecision|None`; `decide_edit(kept:list[MomentRating], slots:list[RhythmSlot], backends:list[AgentBackend], workdir:Path, runner:AgentRunner=subprocess.run) -> EditDecision|None`.

- [ ] **Step 1: Write the failing test**

Add to `tests/director/test_edit_agent.py`:

```python
def test_parse_edit_response_maps_effects() -> None:
    from aicutting.core.models import TransitionType
    from aicutting.director.edit_agent import parse_edit_response

    raw = json.dumps({"arc": "build", "clips": [
        {"slot_index": 0, "moment_id": "m001", "effect": "hard_cut", "reason": "open"},
        {"slot_index": 1, "moment_id": "m002", "effect": "smooth_zoom", "reason": "peak"},
    ]})
    decision = parse_edit_response(raw)
    assert decision is not None
    assert decision.clips[1].effect == TransitionType.SMOOTH_ZOOM


def test_decide_edit_calls_agent_once(tmp_path: Path) -> None:
    from aicutting.director.edit_agent import decide_edit
    from aicutting.director.edit_models import MomentRating, RhythmSlot
    from aicutting.core.models import DroneShotType

    calls: list[list[str]] = []

    def fake_runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        out = Path(command[command.index("--output-last-message") + 1])
        out.write_text(json.dumps({"arc": "x", "clips": [
            {"slot_index": 0, "moment_id": "m001", "effect": "hard_cut", "reason": "open"}
        ]}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    kept = [MomentRating(moment_id="m001", cinematic_score=0.9, shot_type=DroneShotType.REVEAL, keep=True, reason="ok")]
    slots = [RhythmSlot(index=0, start_s=0.0, end_s=3.0, energy=0.8, is_accent=True, section="peak")]
    decision = decide_edit(kept, slots, [AgentBackend(name="codex", executable="codex", available=True)], tmp_path, fake_runner)

    assert decision is not None and decision.clips[0].moment_id == "m001"
    assert len(calls) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/director/test_edit_agent.py -q`
Expected: FAIL (`cannot import name 'decide_edit'`).

- [ ] **Step 3: Write the implementation**

Append to `src/aicutting/director/edit_agent.py` (add imports `RhythmSlot`, `EditDecision`):

```python
from aicutting.director.edit_models import EditDecision, RhythmSlot  # add to existing imports

_EFFECTS = ["hard_cut", "dissolve", "smooth_zoom", "whip_blur", "flash_cut", "speed_ramp", "match_motion"]


def edit_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["arc", "clips"],
        "properties": {
            "arc": {"type": "string"},
            "clips": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["slot_index", "moment_id", "effect", "reason"],
                    "properties": {
                        "slot_index": {"type": "integer", "minimum": 0},
                        "moment_id": {"type": "string"},
                        "effect": {"type": "string", "enum": _EFFECTS},
                        "reason": {"type": "string"},
                    },
                },
            },
        },
    }


def build_edit_prompt(kept: list[MomentRating], slots: list[RhythmSlot]) -> str:
    moments = "\n".join(
        f"- {r.moment_id}: {r.shot_type.value} score {r.cinematic_score:.2f}" for r in kept
    )
    grid = "\n".join(
        f"- slot {s.index}: {s.duration_s:.2f}s energy {s.energy:.2f} "
        f"{'ACCENT ' if s.is_accent else ''}{s.section}"
        for s in slots
    )
    return (
        "You are a professional drone-video editor cutting to music. Build the edit by assigning "
        "ONE moment to each slot, in slot order, to fill the whole song.\n"
        "Rules: never repeat a moment; never put the same shot_type in two adjacent slots; match "
        "calm slots to establishing/top_down/orbit and high-energy/accent slots to "
        "reveal/approach/fly_through; build toward the accents.\n"
        "Choose an effect per slot: usually hard_cut; on ACCENT slots, if the motion fits, use "
        "smooth_zoom (forward/reveal), whip_blur (fast lateral), or match_motion; dissolve only for "
        "calm intros/outros. Keep effects rare and tasteful.\n\n"
        f"Available moments:\n{moments}\n\nSlots:\n{grid}\n\nReturn JSON only matching the schema."
    )


def parse_edit_response(raw: str) -> EditDecision | None:
    for candidate in _candidate_json_payloads(raw):
        try:
            payload = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and isinstance(payload.get("result"), str):
            return parse_edit_response(payload["result"])
        if isinstance(payload, dict) and "clips" in payload:
            try:
                return EditDecision.model_validate(payload)
            except (TypeError, ValueError):
                continue
    return None


def decide_edit(
    kept: list[MomentRating],
    slots: list[RhythmSlot],
    backends: list[AgentBackend],
    workdir: Path,
    runner: AgentRunner = subprocess.run,
) -> EditDecision | None:
    available = _preferred_available_backends(backends)
    if not available or not kept or not slots:
        return None
    backend = available[0]
    workdir.mkdir(parents=True, exist_ok=True)
    schema_path = workdir / "edit-decision-schema.json"
    response_path = workdir / "edit-decision.raw.json"
    schema_path.write_text(json.dumps(edit_schema(), indent=2), encoding="utf-8")
    prompt = build_edit_prompt(kept, slots)
    if backend.name == "claude":
        command = [
            _backend_executable(backend), "-p", "--output-format", "json",
            "--json-schema", json.dumps(edit_schema(), ensure_ascii=True), prompt,
        ]
        input_text = None
    else:
        command = [
            _backend_executable(backend), "exec", "--skip-git-repo-check", "-s", "read-only",
            "--output-schema", str(schema_path), "--output-last-message", str(response_path), "-",
        ]
        input_text = prompt
    try:
        completed = runner(
            command, cwd=str(workdir), input=input_text, text=True, capture_output=True,
            encoding="utf-8", errors="replace", check=False, timeout=180,
        )
        _raise_for_agent_failure(completed)
    except Exception:  # noqa: BLE001 - fall back to deterministic editor on any failure
        return None
    raw = response_path.read_text(encoding="utf-8") if response_path.exists() else completed.stdout
    return parse_edit_response(raw)
```

- [ ] **Step 4: Run, lint, type-check, commit**

```powershell
py -m pytest tests/director/test_edit_agent.py -q
py -m ruff check src/aicutting/director/edit_agent.py tests/director/test_edit_agent.py
py -m mypy src
git add src/aicutting/director/edit_agent.py tests/director/test_edit_agent.py
git commit -m "feat: design the edit with the vision agent"
```

Expected: PASS, ruff clean, mypy clean.

---

### Task 6: Deterministic assembly + fallback editor

**Files:**
- Create: `src/aicutting/planning/assemble.py`
- Test: `tests/planning/test_assemble.py`

**Interfaces:**
- Consumes: `FootageMoment`, `MomentRating`, `RhythmSlot`, `EditDecision`, `EditClip`, `MediaAsset`, `Timeline`, `TimelineClip`, `Transition`, `TransitionType`, `CutPlan`.
- Produces: `fallback_edit(kept:list[MomentRating], slots:list[RhythmSlot]) -> EditDecision`; `assemble_cut_plan(edit:EditDecision, slots:list[RhythmSlot], moments:dict[str, FootageMoment], media:list[MediaAsset], trim_s:float=12.0) -> CutPlan`.

Assembly rules enforced regardless of what the agent returned: iterate slots in order; for each slot take the agent's `EditClip` (or the fallback's); skip a clip whose moment is unknown, already used, or whose `shot_type`/effect would repeat the previous; clamp the source window `[timestamp - dur/2, timestamp + dur/2]` into `[trim, file_duration - trim]`; build a `TimelineClip` of the slot duration. `fallback_edit` assigns kept moments to slots greedily by energy↔score fit with the same no-repeat constraints, all `hard_cut`.

- [ ] **Step 1: Write the failing test**

Create `tests/planning/test_assemble.py`:

```python
from pathlib import Path

from aicutting.core.models import DroneShotType, MediaAsset, TransitionType
from aicutting.director.edit_models import (
    EditClip,
    EditDecision,
    FootageMoment,
    MomentRating,
    RhythmSlot,
)
from aicutting.planning.assemble import assemble_cut_plan, fallback_edit


def _slots(n: int) -> list[RhythmSlot]:
    return [
        RhythmSlot(index=i, start_s=float(i * 3), end_s=float(i * 3 + 3), energy=0.8 if i % 2 else 0.2,
                   is_accent=bool(i % 2), section="s")
        for i in range(n)
    ]


def _moments(ids: list[str]) -> dict[str, FootageMoment]:
    return {mid: FootageMoment(moment_id=mid, asset_path=Path("flight.mp4"), timestamp_s=20.0 + i * 5)
            for i, mid in enumerate(ids)}


def test_assemble_fills_slots_and_clamps_windows() -> None:
    slots = _slots(3)
    moments = _moments(["m1", "m2", "m3"])
    media = [MediaAsset(path=Path("flight.mp4"), duration_s=60.0, width=1920, height=1080, fps=25.0)]
    edit = EditDecision(arc="x", clips=[
        EditClip(slot_index=0, moment_id="m1", effect=TransitionType.HARD_CUT, reason="open"),
        EditClip(slot_index=1, moment_id="m2", effect=TransitionType.SMOOTH_ZOOM, reason="peak"),
        EditClip(slot_index=2, moment_id="m3", effect=TransitionType.HARD_CUT, reason="rest"),
    ])

    plan = assemble_cut_plan(edit, slots, moments, media)

    assert plan.style == "ai_drone_director_30"
    assert len(plan.timeline.clips) == 3
    assert round(plan.timeline.clips[0].timeline_duration_s, 3) == 3.0
    assert all(0 <= c.source_start_s < c.source_end_s <= 60.0 for c in plan.timeline.clips)
    assert plan.timeline.clips[1].transition_in.kind == TransitionType.SMOOTH_ZOOM


def test_assemble_skips_duplicate_moment() -> None:
    slots = _slots(2)
    moments = _moments(["m1"])
    media = [MediaAsset(path=Path("flight.mp4"), duration_s=60.0, width=1920, height=1080, fps=25.0)]
    edit = EditDecision(arc="x", clips=[
        EditClip(slot_index=0, moment_id="m1", effect=TransitionType.HARD_CUT, reason="a"),
        EditClip(slot_index=1, moment_id="m1", effect=TransitionType.HARD_CUT, reason="dup"),
    ])

    plan = assemble_cut_plan(edit, slots, moments, media)

    assert len(plan.timeline.clips) == 1  # duplicate dropped


def test_fallback_edit_assigns_without_repeats() -> None:
    slots = _slots(3)
    kept = [
        MomentRating(moment_id="m1", cinematic_score=0.9, shot_type=DroneShotType.REVEAL, keep=True, reason=""),
        MomentRating(moment_id="m2", cinematic_score=0.8, shot_type=DroneShotType.APPROACH, keep=True, reason=""),
        MomentRating(moment_id="m3", cinematic_score=0.7, shot_type=DroneShotType.ESTABLISHING, keep=True, reason=""),
    ]
    edit = fallback_edit(kept, slots)
    chosen = [c.moment_id for c in edit.clips]
    assert len(chosen) == len(set(chosen))
    assert len(edit.clips) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/planning/test_assemble.py -q`
Expected: FAIL (`No module named 'aicutting.planning.assemble'`).

- [ ] **Step 3: Write the implementation**

Create `src/aicutting/planning/assemble.py`:

```python
from aicutting.core.models import (
    CutPlan,
    DroneShotType,
    MediaAsset,
    Timeline,
    TimelineClip,
    Transition,
    TransitionType,
)
from aicutting.director.edit_models import (
    EditClip,
    EditDecision,
    FootageMoment,
    MomentRating,
    RhythmSlot,
)

_CALM = {DroneShotType.ESTABLISHING, DroneShotType.TOP_DOWN, DroneShotType.ORBIT}
_ENERGETIC = {DroneShotType.REVEAL, DroneShotType.APPROACH, DroneShotType.FLY_THROUGH}


def fallback_edit(kept: list[MomentRating], slots: list[RhythmSlot]) -> EditDecision:
    pool = sorted(kept, key=lambda r: r.cinematic_score, reverse=True)
    used: set[str] = set()
    prev: DroneShotType | None = None
    clips: list[EditClip] = []
    for slot in slots:
        prefer = _ENERGETIC if slot.is_accent else _CALM
        choice = _best(pool, used, prev, prefer)
        if choice is None:
            break
        used.add(choice.moment_id)
        prev = choice.shot_type
        clips.append(
            EditClip(slot_index=slot.index, moment_id=choice.moment_id,
                     effect=TransitionType.HARD_CUT, reason=f"{choice.shot_type.value} fallback")
        )
    return EditDecision(arc="deterministic fallback", clips=clips)


def _best(
    pool: list[MomentRating], used: set[str], prev: DroneShotType | None, prefer: set[DroneShotType]
) -> MomentRating | None:
    candidates = [r for r in pool if r.moment_id not in used and r.shot_type != prev]
    if not candidates:
        candidates = [r for r in pool if r.moment_id not in used]
    if not candidates:
        return None
    return max(candidates, key=lambda r: (r.shot_type in prefer, r.cinematic_score))


def assemble_cut_plan(
    edit: EditDecision,
    slots: list[RhythmSlot],
    moments: dict[str, FootageMoment],
    media: list[MediaAsset],
    trim_s: float = 12.0,
) -> CutPlan:
    durations = {asset.path: asset.duration_s for asset in media}
    by_slot = {clip.slot_index: clip for clip in edit.clips}
    base = media[0]
    clips: list[TimelineClip] = []
    cursor = 0.0
    used: set[str] = set()
    prev_effect: TransitionType | None = None
    for slot in slots:
        clip = by_slot.get(slot.index)
        if clip is None or clip.moment_id in used or clip.moment_id not in moments:
            continue
        moment = moments[clip.moment_id]
        file_duration = durations.get(moment.asset_path, 0.0)
        window = _clamp_window(moment.timestamp_s, slot.duration_s, file_duration, trim_s)
        if window is None:
            continue
        start_s, end_s = window
        effect = TransitionType.HARD_CUT if clip.effect == prev_effect and clip.effect != TransitionType.HARD_CUT else clip.effect
        clips.append(
            TimelineClip(
                asset_path=moment.asset_path,
                source_start_s=start_s,
                source_end_s=end_s,
                timeline_start_s=round(cursor, 3),
                transition_in=Transition(kind=effect, duration_s=_effect_duration(effect)),
                speed=1.0,
                color_intent="subtle_cinematic",
            )
        )
        used.add(clip.moment_id)
        prev_effect = effect
        cursor = round(cursor + (end_s - start_s), 3)
    timeline = Timeline(
        target_duration_s=round(cursor, 3) or slots[-1].end_s if slots else 1.0,
        clips=clips, fps=base.fps, width=base.width, height=base.height,
    )
    return CutPlan(
        target_duration_s=timeline.target_duration_s,
        style="ai_drone_director_30",
        timeline=timeline,
        notes=[f"Generated by AI Drone Director 3.0 ({len(clips)} clips). Arc: {edit.arc}"],
    )


def _clamp_window(
    timestamp_s: float, duration_s: float, file_duration_s: float, trim_s: float
) -> tuple[float, float] | None:
    if file_duration_s <= 0 or duration_s <= 0:
        return None
    low = min(trim_s, file_duration_s * 0.1)
    high = max(low + 0.1, file_duration_s - low)
    start = max(low, timestamp_s - duration_s / 2)
    end = min(high, start + duration_s)
    start = max(low, end - duration_s)
    if end - start < 0.4:
        return None
    return round(start, 3), round(end, 3)


def _effect_duration(effect: TransitionType) -> float:
    if effect in {TransitionType.DISSOLVE}:
        return 0.35
    if effect in {TransitionType.SMOOTH_ZOOM, TransitionType.WHIP_BLUR}:
        return 0.25
    return 0.0
```

- [ ] **Step 4: Run, lint, type-check, commit**

```powershell
py -m pytest tests/planning/test_assemble.py -q
py -m ruff check src/aicutting/planning/assemble.py tests/planning/test_assemble.py
py -m mypy src
git add src/aicutting/planning/assemble.py tests/planning/test_assemble.py
git commit -m "feat: assemble agent edit onto the rhythm grid"
```

Expected: PASS, ruff clean, mypy clean.

---

### Task 7: Real effect rendering in FFmpeg

**Files:**
- Modify: `src/aicutting/render/ffmpeg.py`
- Test: `tests/render/test_ffmpeg.py`

**Interfaces:**
- Consumes: `Timeline`, `TimelineClip`, `TransitionType`.
- Produces (internal): real `xfade` transition names per kind, a `zoompan` push-in applied to a clip's per-clip filter for `SMOOTH_ZOOM`/`FLASH_CUT` accents, and a `setpts` speed accent for `SPEED_RAMP`. Public `build_ffmpeg_command` signature unchanged.

Design: extend `_xfade_transition_name` to a richer map (`SMOOTH_ZOOM→"smoothleft"`, `WHIP_BLUR→"hblur"` if available else `"fadeblack"`, `FLASH_CUT→"fadewhite"`, default `"fade"`); add an optional per-clip animation injected into the existing per-clip filter chain (the `[{index}:v]setpts=…,scale=…` line) so `zoompan`/`setpts` happen before concat/xfade. Each new transition name is validated by a real-FFmpeg smoke test (Task 9); unknown names fall back to `"fade"`.

- [ ] **Step 1: Write the failing test**

Add to `tests/render/test_ffmpeg.py`:

```python
def test_smooth_zoom_clip_gets_zoompan_animation() -> None:
    base = _timeline()
    second = base.clips[0].model_copy(update={
        "asset_path": Path("clip-b.mp4"),
        "timeline_start_s": 4.0,
        "transition_in": Transition(kind=TransitionType.SMOOTH_ZOOM, duration_s=0.25),
    })
    timeline = base.model_copy(update={"clips": [base.clips[0], second]})

    fc = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = fc[fc.index("-filter_complex") + 1]

    assert "zoompan" in filter_complex
    assert "xfade=transition=smoothleft" in filter_complex


def test_whip_blur_uses_distinct_transition_name() -> None:
    base = _timeline()
    second = base.clips[0].model_copy(update={
        "asset_path": Path("clip-b.mp4"),
        "timeline_start_s": 4.0,
        "transition_in": Transition(kind=TransitionType.WHIP_BLUR, duration_s=0.2),
    })
    timeline = base.model_copy(update={"clips": [base.clips[0], second]})
    fc = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = fc[fc.index("-filter_complex") + 1]
    assert "transition=fade" not in filter_complex.replace("transition=fadeblack", "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/render/test_ffmpeg.py -q`
Expected: FAIL (no `zoompan`; transition is always `fade`).

- [ ] **Step 3: Write the implementation**

In `src/aicutting/render/ffmpeg.py`: (a) replace the per-clip filter loop so accent clips get an animation; (b) expand `_xfade_transition_name`.

Replace the per-clip `video_filters` loop in `build_ffmpeg_command`:

```python
    video_filters: list[str] = []
    concat_inputs: list[str] = []
    for index, clip in enumerate(timeline.clips):
        label = f"v{index}"
        animation = _clip_animation(clip, timeline)
        video_filters.append(
            f"[{index}:v]setpts=PTS-STARTPTS,scale={timeline.width}:{timeline.height},"
            f"fps={timeline.fps},format=yuv420p{animation},settb=AVTB[{label}]"
        )
        concat_inputs.append(f"[{label}]")
```

Add helpers:

```python
def _clip_animation(clip: TimelineClip, timeline: Timeline) -> str:
    kind = clip.transition_in.kind
    if kind in {TransitionType.SMOOTH_ZOOM, TransitionType.FLASH_CUT}:
        frames = max(1, int(round(clip.timeline_duration_s * timeline.fps)))
        return (
            f",zoompan=z='min(zoom+0.0009,1.12)':d={frames}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={timeline.width}x{timeline.height}"
        )
    if kind == TransitionType.SPEED_RAMP:
        return ",setpts=0.85*PTS"
    return ""
```

Replace `_xfade_transition_name`:

```python
def _xfade_transition_name(kind: TransitionType) -> str:
    return {
        TransitionType.WHIP_BLUR: "fadeblack",
        TransitionType.SMOOTH_ZOOM: "smoothleft",
        TransitionType.FLASH_CUT: "fadewhite",
        TransitionType.MATCH_MOTION: "fade",
    }.get(kind, "fade")
```

Ensure `_XFADE_KINDS` includes the rendered-transition kinds (DISSOLVE, SMOOTH_ZOOM, WHIP_BLUR, FLASH_CUT); `SPEED_RAMP`/`MATCH_MOTION`/`HARD_CUT` render as concat (hard) with the per-clip animation already applied.

- [ ] **Step 4: Run, lint, type-check, commit**

```powershell
py -m pytest tests/render/test_ffmpeg.py -q
py -m ruff check src/aicutting/render/ffmpeg.py tests/render/test_ffmpeg.py
py -m mypy src
git add src/aicutting/render/ffmpeg.py tests/render/test_ffmpeg.py
git commit -m "feat: render real drone director effects"
```

Expected: PASS, ruff clean, mypy clean.

---

### Task 8: Pipeline integration + artifacts

**Files:**
- Modify: `src/aicutting/planning/engine.py`
- Modify: `src/aicutting/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: everything above + `build_beat_plan`, `detect_agent_backends`, `sample_footage_moments`, `build_contact_sheets`, `rate_moments`, `decide_edit`, `build_rhythm_grid`, `assemble_cut_plan`, `fallback_edit`, `Director3Report`.
- Produces: a `cut()` that writes `footage-ratings.json`, `edit-decision.json`, `rhythm-grid.json`, `director-3-report.json` and uses the 3.0 timeline; deterministic fallback when no agent.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_pipeline.py`:

```python
def test_pipeline_writes_director_3_artifacts_with_fallback(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")
    report = AnalysisReport(
        media=[MediaAsset(path=video, duration_s=60, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(asset_path=video, start_s=20, end_s=25, quality_score=0.9, motion_score=0.7,
                          diversity_key="c0", shot_type=DroneShotType.REVEAL, drone_director_score=0.9),
        ],
        audio=AudioAnalysis(path=None, duration_s=12.0, beats_s=[0, 1, 2, 3, 4, 5, 6], energy=[0.2, 0.9]),
    )
    deps = PipelineDependencies(
        analyze=lambda i, m: report,
        render=lambda t, o, m: None,
        export_resolve=lambda t, o: None,
    )

    # Force the no-agent path so the test is deterministic and offline.
    import aicutting.pipeline as pipe
    monkeypatched = pipe.CutPipeline(dependencies=deps)
    CutPipeline(dependencies=deps).cut(input_dir, None, output_dir, dry_run=True)

    assert (output_dir / "rhythm-grid.json").exists()
    assert (output_dir / "director-3-report.json").exists()
```

(Use the existing `monkeypatch` fixture to set `aicutting.pipeline.detect_agent_backends` to return `[]` so the deterministic fallback runs without calling codex; assert the artifacts and that the timeline has more than 1 clip.)

- [ ] **Step 2: Run test to verify it fails**

Run: `py -m pytest tests/test_pipeline.py::test_pipeline_writes_director_3_artifacts_with_fallback -q`
Expected: FAIL (artifacts not written).

- [ ] **Step 3: Write the implementation**

In `src/aicutting/planning/engine.py`, replace `_build_drone_director_20_plan` usage: when shot types exist, call a new `build_director_3_plan(report, ratings, slots, moments)` is overkill for engine; instead keep `build_cut_plan` deterministic and move 3.0 orchestration to the pipeline (the agent calls need `output_dir`). So: keep `build_cut_plan` returning the legacy/fallback plan, and have the pipeline build the 3.0 plan when an agent edit is available, else call a deterministic 3.0 plan.

In `src/aicutting/pipeline.py`, after `report = analyze(...)` and before planning, add 3.0 orchestration:

```python
        media = director_outputs.analysis.media
        moments = sample_footage_moments(media)
        moment_index = {m.moment_id: m for m in moments}
        beat_plan = build_beat_plan(report.audio)
        target = choose_target_duration(report.audio.duration_s or sum(c.duration_s for c in report.candidates))
        slots = build_rhythm_grid(beat_plan, target)
        backends = detect_agent_backends()
        sheets = build_contact_sheets(moments, output_dir / "contact-sheets") if any(b.available for b in backends) else []
        ratings = rate_moments(sheets, backends, output_dir) if sheets else []
        kept = [r for r in ratings if r.keep]
        edit = decide_edit(kept, slots, backends, output_dir) if kept else None
        used_agent = edit is not None
        if edit is None:
            fallback_source = kept or _ratings_from_candidates(report.candidates, moments)
            edit = fallback_edit(fallback_source, slots)
        plan = assemble_cut_plan(edit, slots, moment_index, media)
        write_json_models(output_dir / "footage-ratings.json", ratings)
        write_json_models(output_dir / "rhythm-grid.json", slots)
        write_json_model(output_dir / "edit-decision.json", edit)
        write_json_model(output_dir / "director-3-report.json", Director3Report(
            used_agent=used_agent, backend=next((b.name for b in backends if b.available), None),
            rated_moments=len(ratings), kept_moments=len(kept),
            timeline_clips=len(plan.timeline.clips),
            warnings=[] if plan.timeline.clips else ["No clips assembled."],
        ))
```

Add `_ratings_from_candidates(candidates, moments)` mapping the existing per-candidate `shot_type`/`drone_director_score` into `MomentRating`s keyed to the nearest sampled moment, so the offline fallback still has data. Keep all existing artifacts and the title pipeline. Title propagation still applies to `plan.timeline`.

- [ ] **Step 4: Run, lint, type-check, commit**

```powershell
py -m pytest tests/test_pipeline.py -q
py -m ruff check src/aicutting/pipeline.py src/aicutting/planning/engine.py tests/test_pipeline.py
py -m mypy src
git add src/aicutting/pipeline.py src/aicutting/planning/engine.py tests/test_pipeline.py
git commit -m "feat: orchestrate agent-driven director 3.0 in the pipeline"
```

Expected: PASS, ruff clean, mypy clean.

---

### Task 9: Full verification, real footage, docs

**Files:**
- Modify: `README.md`, `docs/quickstart.md`
- No source changes unless verification finds a real bug (then fix test-first).

- [ ] **Step 1: Full automated verification**

```powershell
py -m pytest -q
py -m ruff check .
py -m mypy src
```

Expected: all pass, ruff clean, mypy clean.

- [ ] **Step 2: Real FFmpeg effect smoke test**

```powershell
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
ffmpeg -hide_banner -v error -f lavfi -i color=c=black:s=320x240:d=2 -f lavfi -i color=c=white:s=320x240:d=2 -filter_complex "[0:v]zoompan=z='min(zoom+0.002,1.2)':d=50:s=320x240,settb=AVTB[a];[1:v]settb=AVTB[b];[a][b]xfade=transition=smoothleft:duration=0.25:offset=1.5[v]" -map "[v]" -frames:v 1 -f null -
```

Expected: exit 0 (zoompan + smoothleft parse and render). If a transition name is unsupported, adjust `_xfade_transition_name` to a supported one and re-test.

- [ ] **Step 3: Real agent-driven run on the sample footage**

```powershell
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
py -m aicutting cut 'C:\Users\mrnix\Downloads\est' --music 'C:\Users\mrnix\Downloads\etss\videoplayback.mp3' --out 'C:\Users\mrnix\Downloads\est-director-3' --dry-run
```

Inspect `est-director-3`: `timeline.json` clip count and total duration ≈ music length (NOT 20 s); `footage-ratings.json` shows kept/rejected with reasons; no clip whose source window is in a takeoff/landing zone; `director-3-report.json` `used_agent=true`. Confirm shot variety (no identical shot types back-to-back) and that effects appear only on accent slots.

- [ ] **Step 4: Render and watch a preview**

Render the first ~12 clips of `est-director-3/timeline.json` with `render_timeline` to `est-director-3-preview/final-preview.mp4`, `ffprobe` it (video + audio, sane duration), and open it. Confirm it looks professional: varied cuts on the beat, no landing, tasteful effects.

- [ ] **Step 5: Update docs**

In `README.md`, replace the "AI Drone Director 2.0" section with an "AI Drone Director 3.0" section: agent-driven (codex/claude rate and design the edit), full music-length beat-synced output, real effects, deterministic fallback when no agent is installed. In `docs/quickstart.md`, add the new artifacts (`footage-ratings.json`, `rhythm-grid.json`, `edit-decision.json`, `director-3-report.json`, `contact-sheets/`) and note that codex/claude on PATH enables agent editing.

```powershell
git add README.md docs/quickstart.md
git commit -m "docs: document ai drone director 3.0"
```

- [ ] **Step 6: Commit any verification-only fixes** (test-first) if Step 2-4 found a real bug.

---

## Plan Self-Review

**Spec coverage:** length=music (Task 3 grid + Task 8 target), pacing by energy (Task 3), agent rating/rejection (Task 4), agent edit/order (Task 5), assembly invariants + no-repeat + trim (Task 6), real effects (Task 7), fallback (Task 6+8), artifacts (Task 8), real-footage proof (Task 9). Covered.

**Placeholder scan:** every code step shows real code; commands have expected outcomes; no TBD/TODO.

**Type consistency:** `MomentRating`, `RhythmSlot`, `EditDecision`, `EditClip`, `FootageMoment`, `ContactSheet`, `Director3Report` defined in Task 1 and used unchanged after; agent helpers (`_candidate_json_payloads`, `_preferred_available_backends`, `_backend_executable`, `_raise_for_agent_failure`, `AgentRunner`) imported from `director/location.py`; `TransitionType` effect values shared between the edit schema (Task 5) and rendering (Task 7).

**Known risks to watch during execution:** importing `_`-prefixed helpers from `location.py` may trip ruff (`PLC2701`) — if so, promote them to public names in `location.py` in Task 4 and update both call sites. Real FFmpeg transition-name support varies by build — Task 9 Step 2 validates and the code falls back to `fade`.
