# AiCutting MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a professional Windows-first local CLI/agent MVP that automatically cuts drone and landscape B-roll into a finished video and a DaVinci Resolve handoff.

**Architecture:** Use a deterministic Python pipeline with a central neutral timeline model. Analysis, planning, rendering, Resolve export, and local agent support are separate modules with testable interfaces and JSON artifacts between major stages.

**Tech Stack:** Python 3.11+, Typer, Pydantic v2, Rich, FFmpeg/ffprobe, OpenCV, PySceneDetect, librosa, pytest, Ruff, mypy, GitHub Actions.

---

## Scope Check

The approved spec covers a full MVP with multiple modules. They are sequential rather than independent: domain models enable analysis, analysis enables planning, planning enables render/export, and orchestration ties them together. Implement this as one staged plan with frequent commits and tests after each stage.

## File Structure

Create this structure:

```text
AiCutting/
  .github/
    ISSUE_TEMPLATE/
      bug_report.yml
      feature_request.yml
    workflows/
      ci.yml
    pull_request_template.md
  docs/
    architecture.md
    examples/
      basic-config.toml
    superpowers/
      plans/
        2026-06-20-aicutting-mvp-implementation.md
      specs/
        2026-06-20-aicutting-mvp-design.md
  src/
    aicutting/
      __init__.py
      __main__.py
      cli.py
      core/
        __init__.py
        artifacts.py
        errors.py
        models.py
        paths.py
      analysis/
        __init__.py
        audio.py
        discovery.py
        ffprobe.py
        video.py
      planning/
        __init__.py
        duration.py
        engine.py
        ranking.py
        transitions.py
      render/
        __init__.py
        ffmpeg.py
      resolve/
        __init__.py
        export.py
        fcpxml.py
        edl.py
      agents/
        __init__.py
        backends.py
      pipeline.py
  tests/
    core/
      test_artifacts.py
      test_models.py
      test_paths.py
    analysis/
      test_audio.py
      test_discovery.py
      test_ffprobe.py
      test_video.py
    planning/
      test_duration.py
      test_engine.py
      test_ranking.py
      test_transitions.py
    render/
      test_ffmpeg.py
    resolve/
      test_export.py
      test_fcpxml.py
      test_edl.py
    agents/
      test_backends.py
    test_cli.py
    test_pipeline.py
  LICENSE
  README.md
  pyproject.toml
```

Key boundaries:

- `core` contains shared models, errors, paths, and artifact IO.
- `analysis` extracts deterministic video/audio facts.
- `planning` turns facts into edit decisions.
- `render` produces direct FFmpeg output.
- `resolve` produces editor handoff artifacts.
- `agents` detects Codex and Claude Code without making them required.
- `pipeline.py` orchestrates the full `cut` workflow.
- `cli.py` only parses user input and reports results.

---

### Task 1: Repository Baseline

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `LICENSE`
- Create: `src/aicutting/__init__.py`
- Create: `src/aicutting/__main__.py`
- Create: `src/aicutting/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI smoke test**

Create `tests/test_cli.py`:

```python
from typer.testing import CliRunner

from aicutting.cli import app


def test_version_command_prints_package_name() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "AiCutting" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_cli.py::test_version_command_prints_package_name -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'aicutting'`.

- [ ] **Step 3: Add package metadata and CLI entrypoint**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "aicutting"
version = "0.1.0"
description = "Professional local AI-assisted drone video cutting pipeline."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "AiCutting Contributors" }]
dependencies = [
  "typer>=0.12.5",
  "rich>=13.9",
  "pydantic>=2.8",
  "numpy>=2.0",
  "opencv-python-headless>=4.10",
  "scenedetect[opencv]>=0.6.4",
  "librosa>=0.10.2",
  "soundfile>=0.12.1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3",
  "pytest-cov>=5.0",
  "ruff>=0.6.8",
  "mypy>=1.11",
]

[project.scripts]
aicutting = "aicutting.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/aicutting"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
packages = ["aicutting"]
```

Create `src/aicutting/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/aicutting/cli.py`:

```python
import typer

from aicutting import __version__

app = typer.Typer(help="AiCutting: local cinematic drone video cutting.")


@app.command()
def version() -> None:
    """Print the installed AiCutting version."""
    typer.echo(f"AiCutting {__version__}")
```

Create `src/aicutting/__main__.py`:

```python
from aicutting.cli import app

app()
```

Create `README.md`:

```markdown
# AiCutting

AiCutting is a professional local CLI/agent pipeline for automatically cutting drone and landscape B-roll into clean cinematic edits.

The MVP targets Windows first and produces both a direct FFmpeg render and a DaVinci Resolve handoff from the same neutral timeline.

## MVP Command

```powershell
aicutting cut ./input --music ./music --out ./out
```

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m mypy src
```
```

Create `LICENSE`:

```text
MIT License

Copyright (c) 2026 AiCutting Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pip install -e ".[dev]"
python -m pytest tests/test_cli.py::test_version_command_prints_package_name -v
```

Expected: PASS.

- [ ] **Step 5: Run static checks for the baseline**

Run:

```powershell
python -m ruff check .
python -m mypy src
```

Expected: both commands exit with code 0.

- [ ] **Step 6: Commit**

```powershell
git add pyproject.toml README.md LICENSE src/aicutting tests/test_cli.py
git commit -m "chore: scaffold python cli project"
```

---

### Task 2: Core Models and Artifact IO

**Files:**
- Create: `src/aicutting/core/__init__.py`
- Create: `src/aicutting/core/errors.py`
- Create: `src/aicutting/core/models.py`
- Create: `src/aicutting/core/artifacts.py`
- Create: `tests/core/test_models.py`
- Create: `tests/core/test_artifacts.py`

- [ ] **Step 1: Write failing model tests**

Create `tests/core/test_models.py`:

```python
from pathlib import Path

from aicutting.core.models import (
    AnalysisReport,
    AudioAnalysis,
    ClipCandidate,
    MediaAsset,
    Timeline,
    TimelineClip,
    Transition,
    TransitionType,
)


def test_timeline_model_round_trips() -> None:
    asset = MediaAsset(path=Path("clip.mp4"), duration_s=12.0, width=3840, height=2160, fps=25.0)
    clip = TimelineClip(
        asset_path=asset.path,
        source_start_s=1.0,
        source_end_s=5.0,
        timeline_start_s=0.0,
        transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
        speed=1.0,
        color_intent="neutral",
    )
    timeline = Timeline(target_duration_s=4.0, clips=[clip], fps=25.0, width=3840, height=2160)

    payload = timeline.model_dump(mode="json")
    restored = Timeline.model_validate(payload)

    assert restored.clips[0].asset_path == Path("clip.mp4")
    assert restored.target_duration_s == 4.0


def test_analysis_report_exposes_best_candidates() -> None:
    report = AnalysisReport(
        media=[MediaAsset(path=Path("a.mp4"), duration_s=10.0, width=1920, height=1080, fps=25.0)],
        candidates=[
            ClipCandidate(asset_path=Path("a.mp4"), start_s=0.0, end_s=3.0, quality_score=0.8, motion_score=0.4, diversity_key="lake"),
            ClipCandidate(asset_path=Path("a.mp4"), start_s=3.0, end_s=6.0, quality_score=0.4, motion_score=0.9, diversity_key="lake"),
        ],
        audio=AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[]),
    )

    assert report.best_candidates(limit=1)[0].quality_score == 0.8
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/core/test_models.py -v
```

Expected: FAIL with missing `aicutting.core.models`.

- [ ] **Step 3: Implement core models**

Create `src/aicutting/core/__init__.py`:

```python
"""Core domain types and shared infrastructure for AiCutting."""
```

Create `src/aicutting/core/errors.py`:

```python
class AiCuttingError(Exception):
    """Base exception for expected AiCutting failures."""


class ValidationError(AiCuttingError):
    """Raised when user input or environment validation fails."""


class ExternalToolError(AiCuttingError):
    """Raised when FFmpeg, ffprobe, Resolve, or another external tool fails."""
```

Create `src/aicutting/core/models.py`:

```python
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class MediaAsset(BaseModel):
    path: Path
    duration_s: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: float = Field(gt=0)


class AudioAnalysis(BaseModel):
    path: Path | None
    duration_s: float = Field(ge=0)
    beats_s: list[float]
    energy: list[float]


class ClipCandidate(BaseModel):
    asset_path: Path
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    quality_score: float = Field(ge=0, le=1)
    motion_score: float = Field(ge=0, le=1)
    diversity_key: str

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

    @property
    def composite_score(self) -> float:
        return round((self.quality_score * 0.7) + (self.motion_score * 0.3), 6)


class AnalysisReport(BaseModel):
    media: list[MediaAsset]
    candidates: list[ClipCandidate]
    audio: AudioAnalysis

    def best_candidates(self, limit: int) -> list[ClipCandidate]:
        return sorted(self.candidates, key=lambda item: item.composite_score, reverse=True)[:limit]


class TransitionType(StrEnum):
    HARD_CUT = "hard_cut"
    DISSOLVE = "dissolve"
    MATCH_CUT = "match_cut"


class Transition(BaseModel):
    kind: TransitionType
    duration_s: float = Field(ge=0)


class TimelineClip(BaseModel):
    asset_path: Path
    source_start_s: float = Field(ge=0)
    source_end_s: float = Field(gt=0)
    timeline_start_s: float = Field(ge=0)
    transition_in: Transition
    speed: float = Field(gt=0)
    color_intent: str

    @property
    def source_duration_s(self) -> float:
        return self.source_end_s - self.source_start_s

    @property
    def timeline_duration_s(self) -> float:
        return self.source_duration_s / self.speed


class Timeline(BaseModel):
    target_duration_s: float = Field(gt=0)
    clips: list[TimelineClip]
    fps: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class CutPlan(BaseModel):
    target_duration_s: float = Field(gt=0)
    style: str
    timeline: Timeline
    notes: list[str]
```

- [ ] **Step 4: Run model tests to verify they pass**

Run:

```powershell
python -m pytest tests/core/test_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Write failing artifact IO tests**

Create `tests/core/test_artifacts.py`:

```python
from pathlib import Path

from aicutting.core.artifacts import read_json_model, write_json_model
from aicutting.core.models import AudioAnalysis


def test_write_and_read_json_model(tmp_path: Path) -> None:
    artifact = tmp_path / "audio.json"
    model = AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[])

    write_json_model(artifact, model)
    restored = read_json_model(artifact, AudioAnalysis)

    assert restored == model
    assert artifact.read_text(encoding="utf-8").endswith("\n")
```

- [ ] **Step 6: Run artifact test to verify it fails**

Run:

```powershell
python -m pytest tests/core/test_artifacts.py -v
```

Expected: FAIL with missing `aicutting.core.artifacts`.

- [ ] **Step 7: Implement artifact IO**

Create `src/aicutting/core/artifacts.py`:

```python
import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def write_json_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = model.model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json_model(path: Path, model_type: type[ModelT]) -> ModelT:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return model_type.model_validate(payload)
```

- [ ] **Step 8: Run core tests**

Run:

```powershell
python -m pytest tests/core -v
python -m ruff check src tests
python -m mypy src
```

Expected: all commands pass.

- [ ] **Step 9: Commit**

```powershell
git add src/aicutting/core tests/core
git commit -m "feat: add core timeline models and artifacts"
```

---

### Task 3: Paths, Tool Validation, and CLI Shape

**Files:**
- Create: `src/aicutting/core/paths.py`
- Modify: `src/aicutting/cli.py`
- Create: `tests/core/test_paths.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing path validation tests**

Create `tests/core/test_paths.py`:

```python
from pathlib import Path

import pytest

from aicutting.core.errors import ValidationError
from aicutting.core.paths import CutInputs, resolve_cut_inputs


def test_resolve_cut_inputs_accepts_existing_video_folder(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    music_dir = tmp_path / "music"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    music_dir.mkdir()

    result = resolve_cut_inputs(input_dir, music_dir, output_dir)

    assert result == CutInputs(input_dir=input_dir, music_path=music_dir, output_dir=output_dir)


def test_resolve_cut_inputs_rejects_missing_input(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="Input folder does not exist"):
        resolve_cut_inputs(tmp_path / "missing", None, tmp_path / "out")
```

- [ ] **Step 2: Run path tests to verify they fail**

Run:

```powershell
python -m pytest tests/core/test_paths.py -v
```

Expected: FAIL with missing `aicutting.core.paths`.

- [ ] **Step 3: Implement path validation**

Create `src/aicutting/core/paths.py`:

```python
from dataclasses import dataclass
from pathlib import Path

from aicutting.core.errors import ValidationError


@dataclass(frozen=True)
class CutInputs:
    input_dir: Path
    music_path: Path | None
    output_dir: Path


def resolve_cut_inputs(input_dir: Path, music_path: Path | None, output_dir: Path) -> CutInputs:
    input_dir = input_dir.expanduser()
    music_path = music_path.expanduser() if music_path is not None else None
    output_dir = output_dir.expanduser()

    if not input_dir.exists():
        raise ValidationError(f"Input folder does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise ValidationError(f"Input path must be a folder: {input_dir}")
    if music_path is not None and not music_path.exists():
        raise ValidationError(f"Music path does not exist: {music_path}")

    return CutInputs(input_dir=input_dir, music_path=music_path, output_dir=output_dir)
```

- [ ] **Step 4: Write failing CLI shape tests**

Append to `tests/test_cli.py`:

```python

def test_cut_command_rejects_missing_input(tmp_path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["cut", str(tmp_path / "missing"), "--out", str(tmp_path / "out")])
    assert result.exit_code != 0
    assert "Input folder does not exist" in result.stdout
```

- [ ] **Step 5: Run CLI test to verify it fails**

Run:

```powershell
python -m pytest tests/test_cli.py::test_cut_command_rejects_missing_input -v
```

Expected: FAIL because the `cut` command does not exist.

- [ ] **Step 6: Add CLI command boundary**

Replace `src/aicutting/cli.py` with:

```python
from pathlib import Path

import typer

from aicutting import __version__
from aicutting.core.errors import AiCuttingError
from aicutting.core.paths import resolve_cut_inputs

app = typer.Typer(help="AiCutting: local cinematic drone video cutting.")


@app.command()
def version() -> None:
    """Print the installed AiCutting version."""
    typer.echo(f"AiCutting {__version__}")


@app.command()
def cut(
    input_dir: Path = typer.Argument(..., help="Folder containing drone videos."),
    music: Path | None = typer.Option(None, "--music", "-m", help="Optional music file or folder."),
    out: Path = typer.Option(..., "--out", "-o", help="Output folder for render and artifacts."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Create artifacts without rendering video."),
) -> None:
    """Run the automatic cinematic cut pipeline."""
    try:
        inputs = resolve_cut_inputs(input_dir=input_dir, music_path=music, output_dir=out)
    except AiCuttingError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2) from exc

    typer.echo(f"Input: {inputs.input_dir}")
    typer.echo(f"Music: {inputs.music_path if inputs.music_path else 'none'}")
    typer.echo(f"Output: {inputs.output_dir}")
    typer.echo(f"Dry run: {dry_run}")
```

- [ ] **Step 7: Run validation and CLI tests**

Run:

```powershell
python -m pytest tests/core/test_paths.py tests/test_cli.py -v
python -m ruff check src tests
python -m mypy src
```

Expected: all commands pass.

- [ ] **Step 8: Commit**

```powershell
git add src/aicutting/cli.py src/aicutting/core/paths.py tests/core/test_paths.py tests/test_cli.py
git commit -m "feat: validate cut inputs in cli"
```

---

### Task 4: Media Discovery and ffprobe Integration

**Files:**
- Create: `src/aicutting/analysis/__init__.py`
- Create: `src/aicutting/analysis/discovery.py`
- Create: `src/aicutting/analysis/ffprobe.py`
- Create: `tests/analysis/test_discovery.py`
- Create: `tests/analysis/test_ffprobe.py`

- [ ] **Step 1: Write failing discovery tests**

Create `tests/analysis/test_discovery.py`:

```python
from pathlib import Path

from aicutting.analysis.discovery import discover_music, discover_videos


def test_discover_videos_returns_supported_files_sorted(tmp_path: Path) -> None:
    (tmp_path / "b.MP4").write_text("", encoding="utf-8")
    (tmp_path / "a.mov").write_text("", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("", encoding="utf-8")

    assert discover_videos(tmp_path) == [tmp_path / "a.mov", tmp_path / "b.MP4"]


def test_discover_music_accepts_single_file(tmp_path: Path) -> None:
    song = tmp_path / "track.wav"
    song.write_text("", encoding="utf-8")

    assert discover_music(song) == song
```

- [ ] **Step 2: Implement discovery**

Create `src/aicutting/analysis/__init__.py`:

```python
"""Media analysis modules."""
```

Create `src/aicutting/analysis/discovery.py`:

```python
from pathlib import Path

from aicutting.core.errors import ValidationError

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac"}


def discover_videos(input_dir: Path) -> list[Path]:
    videos = sorted(
        path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not videos:
        raise ValidationError(f"No supported video files found in {input_dir}")
    return videos


def discover_music(music_path: Path | None) -> Path | None:
    if music_path is None:
        return None
    if music_path.is_file() and music_path.suffix.lower() in AUDIO_EXTENSIONS:
        return music_path
    if music_path.is_dir():
        tracks = sorted(path for path in music_path.iterdir() if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS)
        if tracks:
            return tracks[0]
    raise ValidationError(f"No supported music file found at {music_path}")
```

- [ ] **Step 3: Run discovery tests**

Run:

```powershell
python -m pytest tests/analysis/test_discovery.py -v
```

Expected: PASS.

- [ ] **Step 4: Write failing ffprobe tests**

Create `tests/analysis/test_ffprobe.py`:

```python
import json
import subprocess
from pathlib import Path

import pytest

from aicutting.analysis.ffprobe import probe_video
from aicutting.core.errors import ExternalToolError


def test_probe_video_maps_ffprobe_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_text("", encoding="utf-8")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        payload = {
            "format": {"duration": "12.5"},
            "streams": [{"codec_type": "video", "width": 3840, "height": 2160, "avg_frame_rate": "25/1"}],
        }
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    asset = probe_video(video)

    assert asset.duration_s == 12.5
    assert asset.width == 3840
    assert asset.height == 2160
    assert asset.fps == 25.0


def test_probe_video_raises_external_tool_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_text("", encoding="utf-8")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="bad codec")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ExternalToolError, match="ffprobe failed"):
        probe_video(video)
```

- [ ] **Step 5: Implement ffprobe wrapper**

Create `src/aicutting/analysis/ffprobe.py`:

```python
import json
import subprocess
from pathlib import Path

from aicutting.core.errors import ExternalToolError
from aicutting.core.models import MediaAsset


def _parse_fps(rate: str) -> float:
    numerator, denominator = rate.split("/")
    denominator_value = float(denominator)
    if denominator_value == 0:
        return 0.0
    return float(numerator) / denominator_value


def probe_video(path: Path) -> MediaAsset:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ExternalToolError(f"ffprobe failed for {path}: {result.stderr.strip()}")

    payload = json.loads(result.stdout)
    video_stream = next(stream for stream in payload["streams"] if stream.get("codec_type") == "video")
    return MediaAsset(
        path=path,
        duration_s=float(payload["format"]["duration"]),
        width=int(video_stream["width"]),
        height=int(video_stream["height"]),
        fps=_parse_fps(str(video_stream["avg_frame_rate"])),
    )
```

- [ ] **Step 6: Run analysis tests**

Run:

```powershell
python -m pytest tests/analysis/test_discovery.py tests/analysis/test_ffprobe.py -v
python -m ruff check src tests
python -m mypy src
```

Expected: all commands pass.

- [ ] **Step 7: Commit**

```powershell
git add src/aicutting/analysis tests/analysis
git commit -m "feat: discover media and probe video metadata"
```

---

### Task 5: Deterministic Video and Audio Analysis

**Files:**
- Create: `src/aicutting/analysis/video.py`
- Create: `src/aicutting/analysis/audio.py`
- Create: `tests/analysis/test_video.py`
- Create: `tests/analysis/test_audio.py`

- [ ] **Step 1: Write failing video scoring tests**

Create `tests/analysis/test_video.py`:

```python
from pathlib import Path

import numpy as np

from aicutting.analysis.video import build_candidates_from_scenes, score_frame_quality
from aicutting.core.models import MediaAsset


def test_score_frame_quality_rewards_contrast() -> None:
    flat = np.full((20, 20, 3), 120, dtype=np.uint8)
    contrast = np.zeros((20, 20, 3), dtype=np.uint8)
    contrast[:, 10:] = 255

    assert score_frame_quality(contrast) > score_frame_quality(flat)


def test_build_candidates_from_scenes_skips_tiny_segments() -> None:
    asset = MediaAsset(path=Path("clip.mp4"), duration_s=20.0, width=1920, height=1080, fps=25.0)
    candidates = build_candidates_from_scenes(asset, scenes=[(0.0, 0.5), (1.0, 5.0)], quality_score=0.7, motion_score=0.4)

    assert len(candidates) == 1
    assert candidates[0].start_s == 1.0
```

- [ ] **Step 2: Implement video analysis helpers**

Create `src/aicutting/analysis/video.py`:

```python
from pathlib import Path

import cv2
import numpy as np

from aicutting.core.models import ClipCandidate, MediaAsset


def score_frame_quality(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast = float(gray.std())
    normalized = min(1.0, (sharpness / 500.0) * 0.6 + (contrast / 80.0) * 0.4)
    return round(normalized, 6)


def build_candidates_from_scenes(
    asset: MediaAsset,
    scenes: list[tuple[float, float]],
    quality_score: float,
    motion_score: float,
) -> list[ClipCandidate]:
    candidates: list[ClipCandidate] = []
    for start_s, end_s in scenes:
        if end_s - start_s < 1.0:
            continue
        candidates.append(
            ClipCandidate(
                asset_path=asset.path,
                start_s=start_s,
                end_s=end_s,
                quality_score=quality_score,
                motion_score=motion_score,
                diversity_key=_diversity_key(asset.path, start_s),
            )
        )
    return candidates


def _diversity_key(path: Path, start_s: float) -> str:
    bucket = int(start_s // 10)
    return f"{path.stem}:{bucket}"
```

- [ ] **Step 3: Write failing audio tests**

Create `tests/analysis/test_audio.py`:

```python
from pathlib import Path

from aicutting.analysis.audio import analyze_music


def test_analyze_music_none_returns_empty_audio() -> None:
    analysis = analyze_music(None)

    assert analysis.path is None
    assert analysis.duration_s == 0.0
    assert analysis.beats_s == []
    assert analysis.energy == []


def test_analyze_music_uses_injected_loader(tmp_path: Path) -> None:
    music = tmp_path / "track.wav"
    music.write_text("", encoding="utf-8")

    analysis = analyze_music(music, loader=lambda _: ([0.0, 1.0, 2.0], 3.0, [0.2, 0.9]))

    assert analysis.path == music
    assert analysis.duration_s == 3.0
    assert analysis.beats_s == [0.0, 1.0, 2.0]
    assert analysis.energy == [0.2, 0.9]
```

- [ ] **Step 4: Implement audio analysis**

Create `src/aicutting/analysis/audio.py`:

```python
from collections.abc import Callable
from pathlib import Path

import librosa
import numpy as np

from aicutting.core.models import AudioAnalysis

AudioLoader = Callable[[Path], tuple[list[float], float, list[float]]]


def analyze_music(path: Path | None, loader: AudioLoader | None = None) -> AudioAnalysis:
    if path is None:
        return AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[])
    beats_s, duration_s, energy = loader(path) if loader else _load_with_librosa(path)
    return AudioAnalysis(path=path, duration_s=duration_s, beats_s=beats_s, energy=energy)


def _load_with_librosa(path: Path) -> tuple[list[float], float, list[float]]:
    y, sr = librosa.load(path, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    del tempo
    beats_s = librosa.frames_to_time(beat_frames, sr=sr).round(3).tolist()
    duration_s = float(librosa.get_duration(y=y, sr=sr))
    rms = librosa.feature.rms(y=y)[0]
    energy = np.interp(rms, (float(rms.min()), float(rms.max()) or 1.0), (0.0, 1.0)).round(6).tolist()
    return beats_s, round(duration_s, 3), energy
```

- [ ] **Step 5: Run analysis unit tests**

Run:

```powershell
python -m pytest tests/analysis/test_video.py tests/analysis/test_audio.py -v
python -m ruff check src tests
python -m mypy src
```

Expected: all commands pass.

- [ ] **Step 6: Commit**

```powershell
git add src/aicutting/analysis/video.py src/aicutting/analysis/audio.py tests/analysis/test_video.py tests/analysis/test_audio.py
git commit -m "feat: add deterministic media analysis helpers"
```

---

### Task 6: Planning Engine

**Files:**
- Create: `src/aicutting/planning/__init__.py`
- Create: `src/aicutting/planning/duration.py`
- Create: `src/aicutting/planning/ranking.py`
- Create: `src/aicutting/planning/transitions.py`
- Create: `src/aicutting/planning/engine.py`
- Create: `tests/planning/test_duration.py`
- Create: `tests/planning/test_ranking.py`
- Create: `tests/planning/test_transitions.py`
- Create: `tests/planning/test_engine.py`

- [ ] **Step 1: Write failing duration tests**

Create `tests/planning/test_duration.py`:

```python
from aicutting.planning.duration import choose_target_duration


def test_choose_target_duration_scales_with_material() -> None:
    assert choose_target_duration(total_usable_s=30.0) == 30.0
    assert choose_target_duration(total_usable_s=180.0) == 75.0
    assert choose_target_duration(total_usable_s=800.0) == 180.0
```

- [ ] **Step 2: Implement duration selection**

Create `src/aicutting/planning/__init__.py`:

```python
"""Edit planning modules."""
```

Create `src/aicutting/planning/duration.py`:

```python
def choose_target_duration(total_usable_s: float) -> float:
    if total_usable_s <= 45.0:
        return round(max(15.0, total_usable_s), 3)
    if total_usable_s <= 240.0:
        return 75.0
    return 180.0
```

- [ ] **Step 3: Write failing ranking tests**

Create `tests/planning/test_ranking.py`:

```python
from pathlib import Path

from aicutting.core.models import ClipCandidate
from aicutting.planning.ranking import rank_candidates


def test_rank_candidates_prefers_score_and_diversity() -> None:
    candidates = [
        ClipCandidate(asset_path=Path("a.mp4"), start_s=0, end_s=4, quality_score=0.9, motion_score=0.4, diversity_key="lake"),
        ClipCandidate(asset_path=Path("b.mp4"), start_s=0, end_s=4, quality_score=0.8, motion_score=0.8, diversity_key="forest"),
        ClipCandidate(asset_path=Path("c.mp4"), start_s=0, end_s=4, quality_score=0.95, motion_score=0.1, diversity_key="lake"),
    ]

    ranked = rank_candidates(candidates)

    assert ranked[0].diversity_key == "lake"
    assert ranked[1].diversity_key == "forest"
```

- [ ] **Step 4: Implement ranking**

Create `src/aicutting/planning/ranking.py`:

```python
from aicutting.core.models import ClipCandidate


def rank_candidates(candidates: list[ClipCandidate]) -> list[ClipCandidate]:
    ranked = sorted(candidates, key=lambda candidate: candidate.composite_score, reverse=True)
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
```

- [ ] **Step 5: Write failing transition tests**

Create `tests/planning/test_transitions.py`:

```python
from pathlib import Path

from aicutting.core.models import ClipCandidate, TransitionType
from aicutting.planning.transitions import choose_transition


def test_choose_transition_defaults_to_hard_cut() -> None:
    previous = ClipCandidate(asset_path=Path("a.mp4"), start_s=0, end_s=4, quality_score=0.8, motion_score=0.3, diversity_key="a")
    current = ClipCandidate(asset_path=Path("b.mp4"), start_s=0, end_s=4, quality_score=0.8, motion_score=0.2, diversity_key="b")

    assert choose_transition(previous, current, beat_energy=0.2).kind == TransitionType.HARD_CUT


def test_choose_transition_uses_dissolve_for_calm_related_motion() -> None:
    previous = ClipCandidate(asset_path=Path("a.mp4"), start_s=0, end_s=4, quality_score=0.8, motion_score=0.2, diversity_key="a")
    current = ClipCandidate(asset_path=Path("b.mp4"), start_s=0, end_s=4, quality_score=0.8, motion_score=0.25, diversity_key="b")

    transition = choose_transition(previous, current, beat_energy=0.1)

    assert transition.kind == TransitionType.DISSOLVE
    assert transition.duration_s == 0.35
```

- [ ] **Step 6: Implement transitions**

Create `src/aicutting/planning/transitions.py`:

```python
from aicutting.core.models import ClipCandidate, Transition, TransitionType


def choose_transition(
    previous: ClipCandidate | None,
    current: ClipCandidate,
    beat_energy: float,
) -> Transition:
    if previous is None:
        return Transition(kind=TransitionType.HARD_CUT, duration_s=0.0)
    motion_delta = abs(previous.motion_score - current.motion_score)
    if beat_energy < 0.25 and motion_delta <= 0.1:
        return Transition(kind=TransitionType.DISSOLVE, duration_s=0.35)
    if beat_energy >= 0.75 and motion_delta <= 0.2:
        return Transition(kind=TransitionType.MATCH_CUT, duration_s=0.0)
    return Transition(kind=TransitionType.HARD_CUT, duration_s=0.0)
```

- [ ] **Step 7: Write failing planning engine test**

Create `tests/planning/test_engine.py`:

```python
from pathlib import Path

from aicutting.core.models import AnalysisReport, AudioAnalysis, ClipCandidate, MediaAsset
from aicutting.planning.engine import build_cut_plan


def test_build_cut_plan_creates_timeline_until_target_duration() -> None:
    report = AnalysisReport(
        media=[MediaAsset(path=Path("a.mp4"), duration_s=40, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(asset_path=Path("a.mp4"), start_s=0, end_s=5, quality_score=0.9, motion_score=0.2, diversity_key="a"),
            ClipCandidate(asset_path=Path("a.mp4"), start_s=5, end_s=10, quality_score=0.8, motion_score=0.4, diversity_key="b"),
        ],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )

    plan = build_cut_plan(report)

    assert plan.style == "adaptive_clean_cinematic"
    assert plan.timeline.clips[0].timeline_start_s == 0.0
    assert len(plan.timeline.clips) == 2
```

- [ ] **Step 8: Implement planning engine**

Create `src/aicutting/planning/engine.py`:

```python
from aicutting.core.models import AnalysisReport, CutPlan, Timeline, TimelineClip
from aicutting.planning.duration import choose_target_duration
from aicutting.planning.ranking import rank_candidates
from aicutting.planning.transitions import choose_transition


def build_cut_plan(report: AnalysisReport) -> CutPlan:
    total_usable_s = sum(candidate.duration_s for candidate in report.candidates)
    target_duration_s = choose_target_duration(total_usable_s)
    ranked = rank_candidates(report.candidates)
    base_asset = report.media[0]

    clips: list[TimelineClip] = []
    timeline_cursor = 0.0
    previous = None
    for index, candidate in enumerate(ranked):
        if timeline_cursor >= target_duration_s:
            break
        remaining = target_duration_s - timeline_cursor
        clip_duration = min(candidate.duration_s, remaining, 6.0 if report.audio.beats_s else 5.0)
        energy = report.audio.energy[index % len(report.audio.energy)] if report.audio.energy else 0.2
        transition = choose_transition(previous=previous, current=candidate, beat_energy=energy)
        clips.append(
            TimelineClip(
                asset_path=candidate.asset_path,
                source_start_s=candidate.start_s,
                source_end_s=candidate.start_s + clip_duration,
                timeline_start_s=round(timeline_cursor, 3),
                transition_in=transition,
                speed=1.0,
                color_intent="subtle_cinematic",
            )
        )
        timeline_cursor = round(timeline_cursor + clip_duration, 3)
        previous = candidate

    timeline = Timeline(
        target_duration_s=target_duration_s,
        clips=clips,
        fps=base_asset.fps,
        width=base_asset.width,
        height=base_asset.height,
    )
    return CutPlan(
        target_duration_s=target_duration_s,
        style="adaptive_clean_cinematic",
        timeline=timeline,
        notes=["Generated from deterministic analysis signals."],
    )
```

- [ ] **Step 9: Run planning tests and full unit suite**

Run:

```powershell
python -m pytest tests/planning tests/core -v
python -m ruff check src tests
python -m mypy src
```

Expected: all commands pass.

- [ ] **Step 10: Commit**

```powershell
git add src/aicutting/planning tests/planning
git commit -m "feat: plan adaptive cinematic timelines"
```

---

### Task 7: FFmpeg Render Adapter

**Files:**
- Create: `src/aicutting/render/__init__.py`
- Create: `src/aicutting/render/ffmpeg.py`
- Create: `tests/render/test_ffmpeg.py`

- [ ] **Step 1: Write failing FFmpeg command tests**

Create `tests/render/test_ffmpeg.py`:

```python
from pathlib import Path

from aicutting.core.models import Timeline, TimelineClip, Transition, TransitionType
from aicutting.render.ffmpeg import build_ffmpeg_command


def test_build_ffmpeg_command_contains_trim_and_output() -> None:
    timeline = Timeline(
        target_duration_s=4.0,
        fps=25.0,
        width=1920,
        height=1080,
        clips=[
            TimelineClip(
                asset_path=Path("clip.mp4"),
                source_start_s=1.0,
                source_end_s=5.0,
                timeline_start_s=0.0,
                transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
                speed=1.0,
                color_intent="subtle_cinematic",
            )
        ],
    )

    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)

    assert command[0] == "ffmpeg"
    assert "clip.mp4" in command
    assert "out/final.mp4" in command
    assert any("trim=start=1.0:end=5.0" in part for part in command)
```

- [ ] **Step 2: Implement render command builder**

Create `src/aicutting/render/__init__.py`:

```python
"""Rendering adapters."""
```

Create `src/aicutting/render/ffmpeg.py`:

```python
import subprocess
from pathlib import Path

from aicutting.core.errors import ExternalToolError
from aicutting.core.models import Timeline


def build_ffmpeg_command(timeline: Timeline, output_path: Path, music_path: Path | None) -> list[str]:
    inputs: list[str] = []
    for clip in timeline.clips:
        inputs.extend(["-i", str(clip.asset_path)])
    if music_path is not None:
        inputs.extend(["-i", str(music_path)])

    video_filters: list[str] = []
    concat_inputs: list[str] = []
    for index, clip in enumerate(timeline.clips):
        label = f"v{index}"
        video_filters.append(
            f"[{index}:v]trim=start={clip.source_start_s}:end={clip.source_end_s},"
            f"setpts=PTS-STARTPTS,scale={timeline.width}:{timeline.height},fps={timeline.fps}[{label}]"
        )
        concat_inputs.append(f"[{label}]")

    filter_complex = ";".join(video_filters)
    if concat_inputs:
        filter_complex = f"{filter_complex};{''.join(concat_inputs)}concat=n={len(concat_inputs)}:v=1:a=0[vout]"

    command = ["ffmpeg", "-y", *inputs, "-filter_complex", filter_complex, "-map", "[vout]"]
    if music_path is not None:
        command.extend(["-shortest", "-map", f"{len(timeline.clips)}:a"])
    command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", str(output_path)])
    return command


def render_timeline(timeline: Timeline, output_path: Path, music_path: Path | None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_command(timeline, output_path=output_path, music_path=music_path)
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise ExternalToolError(f"FFmpeg render failed: {result.stderr.strip()}")
```

- [ ] **Step 3: Run render tests**

Run:

```powershell
python -m pytest tests/render/test_ffmpeg.py -v
python -m ruff check src tests
python -m mypy src
```

Expected: all commands pass.

- [ ] **Step 4: Commit**

```powershell
git add src/aicutting/render tests/render
git commit -m "feat: build ffmpeg render command"
```

---

### Task 8: DaVinci Resolve Handoff

**Files:**
- Create: `src/aicutting/resolve/__init__.py`
- Create: `src/aicutting/resolve/fcpxml.py`
- Create: `src/aicutting/resolve/edl.py`
- Create: `src/aicutting/resolve/export.py`
- Create: `tests/resolve/test_fcpxml.py`
- Create: `tests/resolve/test_edl.py`
- Create: `tests/resolve/test_export.py`

- [ ] **Step 1: Write failing FCPXML test**

Create `tests/resolve/test_fcpxml.py`:

```python
from pathlib import Path
import xml.etree.ElementTree as ET

from aicutting.core.models import Timeline, TimelineClip, Transition, TransitionType
from aicutting.resolve.fcpxml import timeline_to_fcpxml


def test_timeline_to_fcpxml_is_parseable() -> None:
    timeline = Timeline(
        target_duration_s=4,
        fps=25,
        width=1920,
        height=1080,
        clips=[
            TimelineClip(
                asset_path=Path("clip.mp4"),
                source_start_s=0,
                source_end_s=4,
                timeline_start_s=0,
                transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0),
                speed=1,
                color_intent="subtle_cinematic",
            )
        ],
    )

    xml_text = timeline_to_fcpxml(timeline)

    root = ET.fromstring(xml_text)
    assert root.tag == "fcpxml"
    assert root.find(".//asset") is not None
```

- [ ] **Step 2: Implement FCPXML export**

Create `src/aicutting/resolve/__init__.py`:

```python
"""DaVinci Resolve handoff exporters."""
```

Create `src/aicutting/resolve/fcpxml.py`:

```python
from xml.etree.ElementTree import Element, SubElement, tostring

from aicutting.core.models import Timeline


def timeline_to_fcpxml(timeline: Timeline) -> str:
    fcpxml = Element("fcpxml", version="1.10")
    resources = SubElement(fcpxml, "resources")
    project = SubElement(fcpxml, "project", name="AiCutting")
    sequence = SubElement(project, "sequence", duration=f"{timeline.target_duration_s}s", format="r1")
    spine = SubElement(sequence, "spine")

    SubElement(
        resources,
        "format",
        id="r1",
        name="AiCuttingFormat",
        frameDuration=f"1/{int(round(timeline.fps))}s",
        width=str(timeline.width),
        height=str(timeline.height),
    )

    asset_ids: dict[str, str] = {}
    for index, clip in enumerate(timeline.clips, start=1):
        key = str(clip.asset_path)
        asset_id = asset_ids.setdefault(key, f"asset{index}")
        if asset_id == f"asset{index}":
            SubElement(resources, "asset", id=asset_id, src=clip.asset_path.as_posix(), name=clip.asset_path.name)
        SubElement(
            spine,
            "asset-clip",
            ref=asset_id,
            name=clip.asset_path.name,
            offset=f"{clip.timeline_start_s}s",
            start=f"{clip.source_start_s}s",
            duration=f"{clip.timeline_duration_s}s",
        )

    return tostring(fcpxml, encoding="unicode") + "\n"
```

- [ ] **Step 3: Write failing EDL and export tests**

Create `tests/resolve/test_edl.py`:

```python
from pathlib import Path

from aicutting.core.models import Timeline, TimelineClip, Transition, TransitionType
from aicutting.resolve.edl import timeline_to_edl


def test_timeline_to_edl_contains_title_and_clip_name() -> None:
    timeline = Timeline(
        target_duration_s=4,
        fps=25,
        width=1920,
        height=1080,
        clips=[
            TimelineClip(
                asset_path=Path("clip.mp4"),
                source_start_s=0,
                source_end_s=4,
                timeline_start_s=0,
                transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0),
                speed=1,
                color_intent="subtle_cinematic",
            )
        ],
    )

    edl = timeline_to_edl(timeline)

    assert "TITLE: AiCutting" in edl
    assert "* FROM CLIP NAME: clip.mp4" in edl
```

Create `tests/resolve/test_export.py`:

```python
from pathlib import Path

from aicutting.core.models import Timeline, TimelineClip, Transition, TransitionType
from aicutting.resolve.export import export_resolve_handoff


def test_export_resolve_handoff_writes_artifacts(tmp_path: Path) -> None:
    timeline = Timeline(
        target_duration_s=4,
        fps=25,
        width=1920,
        height=1080,
        clips=[
            TimelineClip(
                asset_path=Path("clip.mp4"),
                source_start_s=0,
                source_end_s=4,
                timeline_start_s=0,
                transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0),
                speed=1,
                color_intent="subtle_cinematic",
            )
        ],
    )

    export_resolve_handoff(timeline, tmp_path)

    assert (tmp_path / "resolve" / "timeline.fcpxml").exists()
    assert (tmp_path / "resolve" / "timeline.edl").exists()
    assert (tmp_path / "resolve" / "media-manifest.txt").read_text(encoding="utf-8").strip() == "clip.mp4"
```

- [ ] **Step 4: Implement EDL and handoff writer**

Create `src/aicutting/resolve/edl.py`:

```python
from aicutting.core.models import Timeline


def timeline_to_edl(timeline: Timeline) -> str:
    lines = ["TITLE: AiCutting", "FCM: NON-DROP FRAME"]
    for index, clip in enumerate(timeline.clips, start=1):
        lines.append(f"{index:03d}  AX       V     C        00:00:00:00 00:00:04:00 00:00:00:00 00:00:04:00")
        lines.append(f"* FROM CLIP NAME: {clip.asset_path.name}")
    return "\n".join(lines) + "\n"
```

Create `src/aicutting/resolve/export.py`:

```python
from pathlib import Path

from aicutting.core.models import Timeline
from aicutting.resolve.edl import timeline_to_edl
from aicutting.resolve.fcpxml import timeline_to_fcpxml


def export_resolve_handoff(timeline: Timeline, output_dir: Path) -> None:
    resolve_dir = output_dir / "resolve"
    resolve_dir.mkdir(parents=True, exist_ok=True)
    (resolve_dir / "timeline.fcpxml").write_text(timeline_to_fcpxml(timeline), encoding="utf-8")
    (resolve_dir / "timeline.edl").write_text(timeline_to_edl(timeline), encoding="utf-8")
    manifest = "\n".join(str(clip.asset_path) for clip in timeline.clips) + "\n"
    (resolve_dir / "media-manifest.txt").write_text(manifest, encoding="utf-8")
```

- [ ] **Step 5: Run Resolve tests**

Run:

```powershell
python -m pytest tests/resolve -v
python -m ruff check src tests
python -m mypy src
```

Expected: all commands pass.

- [ ] **Step 6: Commit**

```powershell
git add src/aicutting/resolve tests/resolve
git commit -m "feat: export resolve handoff artifacts"
```

---

### Task 9: Local Agent Backend Detection

**Files:**
- Create: `src/aicutting/agents/__init__.py`
- Create: `src/aicutting/agents/backends.py`
- Create: `tests/agents/test_backends.py`

- [ ] **Step 1: Write failing agent backend tests**

Create `tests/agents/test_backends.py`:

```python
import shutil

import pytest

from aicutting.agents.backends import AgentBackend, detect_agent_backends


def test_detect_agent_backends_finds_codex_and_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(name: str) -> str | None:
        return {"codex": "C:/bin/codex.exe", "claude": "C:/bin/claude.exe"}.get(name)

    monkeypatch.setattr(shutil, "which", fake_which)

    assert detect_agent_backends() == [
        AgentBackend(name="codex", executable="C:/bin/codex.exe", available=True),
        AgentBackend(name="claude", executable="C:/bin/claude.exe", available=True),
    ]


def test_detect_agent_backends_reports_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)

    backends = detect_agent_backends()

    assert [backend.available for backend in backends] == [False, False]
```

- [ ] **Step 2: Implement agent detection**

Create `src/aicutting/agents/__init__.py`:

```python
"""Local agent backend detection."""
```

Create `src/aicutting/agents/backends.py`:

```python
from dataclasses import dataclass
import shutil


@dataclass(frozen=True)
class AgentBackend:
    name: str
    executable: str | None
    available: bool


def detect_agent_backends() -> list[AgentBackend]:
    names = ["codex", "claude"]
    return [
        AgentBackend(name=name, executable=shutil.which(name), available=shutil.which(name) is not None)
        for name in names
    ]
```

- [ ] **Step 3: Run agent tests**

Run:

```powershell
python -m pytest tests/agents/test_backends.py -v
python -m ruff check src tests
python -m mypy src
```

Expected: all commands pass.

- [ ] **Step 4: Commit**

```powershell
git add src/aicutting/agents tests/agents
git commit -m "feat: detect local agent backends"
```

---

### Task 10: Pipeline Orchestration

**Files:**
- Create: `src/aicutting/pipeline.py`
- Modify: `src/aicutting/cli.py`
- Create: `tests/test_pipeline.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing pipeline test**

Create `tests/test_pipeline.py`:

```python
from pathlib import Path

from aicutting.core.models import AnalysisReport, AudioAnalysis, ClipCandidate, MediaAsset
from aicutting.pipeline import CutPipeline, PipelineDependencies


def test_pipeline_writes_artifacts_without_rendering(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    video = input_dir / "clip.mp4"
    video.write_text("", encoding="utf-8")

    report = AnalysisReport(
        media=[MediaAsset(path=video, duration_s=8, width=1920, height=1080, fps=25)],
        candidates=[ClipCandidate(asset_path=video, start_s=0, end_s=6, quality_score=0.9, motion_score=0.2, diversity_key="clip:0")],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )

    deps = PipelineDependencies(
        analyze=lambda input_path, music_path: report,
        render=lambda timeline, output_path, music_path: None,
        export_resolve=lambda timeline, out_path: None,
    )
    pipeline = CutPipeline(dependencies=deps)

    result = pipeline.cut(input_dir=input_dir, music_path=None, output_dir=output_dir, dry_run=True)

    assert result.final_video == output_dir / "final.mp4"
    assert (output_dir / "analysis.json").exists()
    assert (output_dir / "cut-plan.json").exists()
    assert (output_dir / "timeline.json").exists()
```

- [ ] **Step 2: Implement pipeline**

Create `src/aicutting/pipeline.py`:

```python
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aicutting.analysis.audio import analyze_music
from aicutting.analysis.discovery import discover_music, discover_videos
from aicutting.analysis.ffprobe import probe_video
from aicutting.analysis.video import build_candidates_from_scenes
from aicutting.core.artifacts import write_json_model
from aicutting.core.models import AnalysisReport, AudioAnalysis, MediaAsset, Timeline
from aicutting.planning.engine import build_cut_plan
from aicutting.render.ffmpeg import render_timeline
from aicutting.resolve.export import export_resolve_handoff


@dataclass(frozen=True)
class PipelineResult:
    analysis: Path
    cut_plan: Path
    timeline: Path
    final_video: Path
    output_dir: Path


@dataclass(frozen=True)
class PipelineDependencies:
    analyze: Callable[[Path, Path | None], AnalysisReport]
    render: Callable[[Timeline, Path, Path | None], None]
    export_resolve: Callable[[Timeline, Path], None]


def default_analyze(input_dir: Path, music_path: Path | None) -> AnalysisReport:
    videos = discover_videos(input_dir)
    music = discover_music(music_path)
    media = [probe_video(path) for path in videos]
    candidates = []
    for asset in media:
        scenes = [(0.0, min(asset.duration_s, 6.0))]
        candidates.extend(build_candidates_from_scenes(asset, scenes, quality_score=0.7, motion_score=0.4))
    audio = analyze_music(music)
    return AnalysisReport(media=media, candidates=candidates, audio=audio)


class CutPipeline:
    def __init__(self, dependencies: PipelineDependencies | None = None) -> None:
        self.dependencies = dependencies or PipelineDependencies(
            analyze=default_analyze,
            render=render_timeline,
            export_resolve=export_resolve_handoff,
        )

    def cut(self, input_dir: Path, music_path: Path | None, output_dir: Path, dry_run: bool) -> PipelineResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        report = self.dependencies.analyze(input_dir, music_path)
        plan = build_cut_plan(report)
        final_video = output_dir / "final.mp4"

        write_json_model(output_dir / "analysis.json", report)
        write_json_model(output_dir / "cut-plan.json", plan)
        write_json_model(output_dir / "timeline.json", plan.timeline)
        self.dependencies.export_resolve(plan.timeline, output_dir)
        if not dry_run:
            self.dependencies.render(plan.timeline, final_video, report.audio.path)

        return PipelineResult(
            analysis=output_dir / "analysis.json",
            cut_plan=output_dir / "cut-plan.json",
            timeline=output_dir / "timeline.json",
            final_video=final_video,
            output_dir=output_dir,
        )
```

- [ ] **Step 3: Wire CLI to pipeline**

Replace the body of the `cut` command in `src/aicutting/cli.py` after successful input validation with:

```python
    from aicutting.pipeline import CutPipeline

    result = CutPipeline().cut(
        input_dir=inputs.input_dir,
        music_path=inputs.music_path,
        output_dir=inputs.output_dir,
        dry_run=dry_run,
    )
    typer.echo(f"Analysis: {result.analysis}")
    typer.echo(f"Cut plan: {result.cut_plan}")
    typer.echo(f"Timeline: {result.timeline}")
    typer.echo(f"Final video: {result.final_video}")
```

- [ ] **Step 4: Add CLI dry-run success test**

Append to `tests/test_cli.py`:

```python

def test_cut_command_dry_run_reports_artifacts(monkeypatch, tmp_path) -> None:
    from aicutting.pipeline import PipelineResult

    input_dir = tmp_path / "input"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    (input_dir / "clip.mp4").write_text("", encoding="utf-8")

    class FakePipeline:
        def cut(self, input_dir, music_path, output_dir, dry_run):
            del input_dir, music_path, dry_run
            output_dir.mkdir(parents=True, exist_ok=True)
            return PipelineResult(
                analysis=output_dir / "analysis.json",
                cut_plan=output_dir / "cut-plan.json",
                timeline=output_dir / "timeline.json",
                final_video=output_dir / "final.mp4",
                output_dir=output_dir,
            )

    monkeypatch.setattr("aicutting.pipeline.CutPipeline", FakePipeline)

    result = CliRunner().invoke(app, ["cut", str(input_dir), "--out", str(output_dir), "--dry-run"])

    assert result.exit_code == 0
    assert "Analysis:" in result.stdout
```

- [ ] **Step 5: Run pipeline and CLI tests**

Run:

```powershell
python -m pytest tests/test_pipeline.py tests/test_cli.py -v
python -m ruff check src tests
python -m mypy src
```

Expected: all commands pass.

- [ ] **Step 6: Commit**

```powershell
git add src/aicutting/pipeline.py src/aicutting/cli.py tests/test_pipeline.py tests/test_cli.py
git commit -m "feat: orchestrate automatic cut pipeline"
```

---

### Task 11: Documentation and GitHub Quality

**Files:**
- Modify: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/examples/basic-config.toml`
- Create: `.github/workflows/ci.yml`
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/feature_request.yml`
- Create: `.github/pull_request_template.md`

- [ ] **Step 1: Expand README with professional usage**

Replace `README.md` with:

```markdown
# AiCutting

AiCutting is a professional local CLI/agent pipeline for automatically cutting drone and landscape B-roll into clean cinematic edits.

It is Windows-first for the MVP, uses deterministic analysis and timeline planning, and produces both a direct FFmpeg render and a DaVinci Resolve handoff.

## What it does

- Finds supported drone video files in an input folder.
- Optionally analyzes a music track for beat and energy information.
- Builds an adaptive clean cinematic timeline.
- Writes `analysis.json`, `cut-plan.json`, and `timeline.json`.
- Renders `final.mp4` with FFmpeg.
- Exports Resolve handoff files under `resolve/`.
- Detects local Codex and Claude Code backends for optional agent workflows.

## Install for development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Basic usage

```powershell
aicutting cut ./input --music ./music --out ./out
```

For a no-render artifact check:

```powershell
aicutting cut ./input --out ./out --dry-run
```

## External tools

Install FFmpeg and ensure `ffmpeg` and `ffprobe` are available on `PATH`.

DaVinci Resolve handoff starts with FCPXML, EDL, and a media manifest. Full Resolve scripting is intentionally separated from the first deterministic handoff path.

## Development checks

```powershell
python -m pytest
python -m ruff check .
python -m mypy src
```
```

- [ ] **Step 2: Add architecture doc**

Create `docs/architecture.md`:

```markdown
# Architecture

AiCutting is built around a neutral timeline core.

## Pipeline

1. Validate input paths and output folder.
2. Discover video and optional music files.
3. Analyze media into `analysis.json`.
4. Build an adaptive clean cinematic `cut-plan.json`.
5. Write the neutral `timeline.json`.
6. Render `final.mp4` with FFmpeg.
7. Export DaVinci Resolve handoff artifacts.

## Module boundaries

- `core`: shared models, errors, path validation, artifact IO.
- `analysis`: deterministic video/audio facts.
- `planning`: target duration, ranking, transitions, timeline construction.
- `render`: FFmpeg command construction and execution.
- `resolve`: FCPXML, EDL, and media manifest export.
- `agents`: local Codex and Claude Code detection.
- `pipeline`: orchestration.

## Long-term rule

Agent features may improve review and configuration, but deterministic artifacts remain the source of truth. This keeps the project testable and usable without paid API calls.
```

- [ ] **Step 3: Add example configuration**

Create `docs/examples/basic-config.toml`:

```toml
[cut]
style = "adaptive_clean_cinematic"
min_clip_seconds = 1.0
max_clip_seconds = 6.0
default_without_music = true

[color]
intent = "subtle_cinematic"
allow_aggressive_grades = false

[resolve]
write_fcpxml = true
write_edl = true
write_media_manifest = true
```

- [ ] **Step 4: Add GitHub Actions CI**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: ["master", "main"]
  pull_request:

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install package
        run: python -m pip install -e ".[dev]"
      - name: Ruff
        run: python -m ruff check .
      - name: Mypy
        run: python -m mypy src
      - name: Pytest
        run: python -m pytest
```

- [ ] **Step 5: Add issue and PR templates**

Create `.github/ISSUE_TEMPLATE/bug_report.yml`:

```yaml
name: Bug report
description: Report a reproducible AiCutting problem.
title: "[Bug]: "
labels: ["bug"]
body:
  - type: textarea
    id: summary
    attributes:
      label: Summary
      description: What happened?
    validations:
      required: true
  - type: textarea
    id: reproduce
    attributes:
      label: Reproduction steps
      description: Include the command you ran and relevant artifact paths.
    validations:
      required: true
  - type: textarea
    id: environment
    attributes:
      label: Environment
      description: Windows version, Python version, FFmpeg version, DaVinci Resolve version.
    validations:
      required: true
```

Create `.github/ISSUE_TEMPLATE/feature_request.yml`:

```yaml
name: Feature request
description: Suggest a focused improvement.
title: "[Feature]: "
labels: ["enhancement"]
body:
  - type: textarea
    id: problem
    attributes:
      label: Problem
      description: What workflow would this improve?
    validations:
      required: true
  - type: textarea
    id: proposal
    attributes:
      label: Proposal
      description: Describe the smallest useful version.
    validations:
      required: true
```

Create `.github/pull_request_template.md`:

```markdown
## Summary

- 

## Verification

- [ ] `python -m pytest`
- [ ] `python -m ruff check .`
- [ ] `python -m mypy src`

## Notes

Describe any media fixtures, external tools, or Resolve-specific behavior needed to review this change.
```

- [ ] **Step 6: Run final repository checks**

Run:

```powershell
python -m pytest
python -m ruff check .
python -m mypy src
```

Expected: all commands pass.

- [ ] **Step 7: Commit**

```powershell
git add README.md docs/architecture.md docs/examples/basic-config.toml .github
git commit -m "docs: add project quality and ci docs"
```

---

## Final Verification

- [ ] Run the full suite:

```powershell
python -m pytest
python -m ruff check .
python -m mypy src
```

Expected: all commands pass.

- [ ] Run CLI smoke checks:

```powershell
aicutting version
aicutting cut ./sample-input --out ./sample-out --dry-run
```

Expected:

- `aicutting version` prints `AiCutting 0.1.0`.
- Dry-run writes `analysis.json`, `cut-plan.json`, `timeline.json`, and Resolve handoff artifacts when `./sample-input` contains at least one supported video file with readable metadata.

- [ ] Inspect Git history:

```powershell
git log --oneline --decorate -10
```

Expected: commits are small, ordered, and reviewable.
