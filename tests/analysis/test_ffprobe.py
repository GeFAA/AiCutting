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
            "streams": [
                {
                    "codec_type": "video",
                    "width": 3840,
                    "height": 2160,
                    "avg_frame_rate": "25/1",
                }
            ],
        }
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(payload), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    asset = probe_video(video)

    assert asset.duration_s == 12.5
    assert asset.width == 3840
    assert asset.height == 2160
    assert asset.fps == 25.0


def test_probe_video_raises_external_tool_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    video = tmp_path / "clip.mp4"
    video.write_text("", encoding="utf-8")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="bad codec")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ExternalToolError, match="ffprobe failed"):
        probe_video(video)
