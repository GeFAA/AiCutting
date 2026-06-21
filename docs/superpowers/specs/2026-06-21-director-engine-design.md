# AiCutting Director Engine Design

Date: 2026-06-21

## Goal

AiCutting needs a professional director layer that makes real editorial decisions
from drone footage instead of only assembling plausible clips. The system must
prefer smooth, usable camera movement, cut to music with intentional timing, reject
takeoff, landing, search-flight, and shaky approach footage with high probability,
and add location/title overlays only when confidence is high enough.

The target result is a local, automatic drone edit that feels curated: the chosen
segments should look like usable B-roll, the transitions should match motion and
music, and the output artifacts should explain why each segment was selected or
rejected.

## Approved Decisions

- Architecture: Hybrid Director Engine.
- Local deterministic analysis owns hard footage decisions.
- Agent backends are optional helpers for visual-language tasks, not the source of
  truth for motion quality.
- Location titles use Hybrid With Confidence:
  - GPS or metadata first when available.
  - Screenshots and agent review second.
  - Automatic render only above a confidence threshold.
  - Low-confidence titles are written as suggestions, not burned into the video.
- Bad flight phases are hard-rejection candidates, not merely low-ranked clips.
- CLI and GUI keep using the same pipeline.
- The implementation must remain local-first and testable without network access.

## User Experience

The normal user still selects:

1. a video folder,
2. an optional song,
3. an output folder,
4. start.

The difference is in the result quality and output transparency. The user should
not need to tune professional editing options to avoid obvious bad footage.

The output folder should include:

- `final.mp4`
- `analysis.json`
- `cut-plan.json`
- `timeline.json`
- `director-report.json`
- `rejected-segments.json`
- `location-suggestions.json`
- optional `contact-sheet.jpg` or per-candidate screenshots for review

When a run has no confident location title, the final video should omit the title
instead of rendering a guessed or embarrassing place name.

## Core Requirements

### Camera Movement Analyzer

The analyzer must evaluate each candidate segment for usable drone motion. It should
sample multiple frames inside each candidate and compute local, deterministic signals:

- frame quality and contrast,
- blur or loss of detail,
- optical-flow magnitude,
- optical-flow consistency,
- direction stability,
- frame-to-frame jitter,
- sudden yaw or pan changes,
- abrupt start/stop motion,
- composition stability over the segment.

The output should extend candidate analysis with:

- `smoothness_score`
- `jitter_score`
- `movement_score`
- `composition_score`
- `usability_score`
- `movement_type`
- `rejection_reason` when rejected

Supported movement types for the first version:

- `push_in`
- `pull_back`
- `orbit`
- `flyover`
- `pan`
- `tilt`
- `static`
- `searching`
- `takeoff_landing`
- `shaky`
- `unknown`

The first implementation does not need perfect classification. It must be useful
enough to strongly penalize or reject obviously bad motion and to explain why.

### Hard Rejection Rules

Segments should be rejected before ranking when strong evidence indicates they are
not usable in a polished drone edit.

Hard rejection reasons:

- `takeoff_or_landing_motion`
- `search_flight_before_subject`
- `unstable_yaw_or_pan`
- `excessive_jitter`
- `abrupt_start_or_stop`
- `low_detail_or_blur`
- `too_static_without_subject`

Takeoff and landing detection should combine signals such as near-ground visual
texture, vertical motion dominance, sudden stabilization changes, shaky early/late
clip movement, and poor composition stability. The implementation should treat the
first and last part of long drone files as suspicious, but not automatically reject
them unless motion and quality evidence supports it.

Search-flight or approach-footage detection should catch segments where the drone is
still moving into position: unstable heading, unresolved composition, repeated small
corrections, or low subject/scene stability. These segments should be excluded with
high probability, even if they are technically sharp.

### Beat Director

Music timing must become a planning signal, not only a rough duration cap.

The planner should:

- cut on or very near beat times when music exists,
- choose shorter cuts for high-energy sections,
- allow longer shots for calmer sections,
- avoid cutting in the middle of a strong smooth movement when a nearby beat would
  produce a better edit,
- prefer hard cuts on strong beats,
- prefer dissolves for calm, related motion,
- prefer match cuts only when motion direction and pace are compatible.

The first implementation may use beat times and normalized energy from the existing
audio analyzer. It should add a small beat-window tolerance and record the chosen
beat or timing reason in the director report.

### Location Title Agent

The title system should be confidence-gated.

Inputs:

- media metadata when available,
- file names and timestamps,
- selected keyframes or screenshots,
- optional EXIF/GPS sidecar data when present.

Agent output must be structured:

- `title`
- `place`
- `confidence`
- `evidence`
- `should_render`

Automatic title rendering rules:

- Render title overlays only when `confidence >= 0.75` and `should_render` is true.
- If confidence is lower, write the suggestion to `location-suggestions.json`.
- If multiple agents are available, deterministic metadata wins over agent guesses.
- Agent guesses must not override a precise GPS-derived place unless explicitly
  marked as higher-confidence metadata enrichment.

The first agent integration should use local command adapters for Codex and Claude
Code when either executable is available, but the pipeline must still run without
either backend.

### Text and Title Rendering

When a title is approved for render, the output should use a clean cinematic lower
third or opening title:

- short place or route title,
- optional date or region subtitle,
- restrained typography,
- no oversized text,
- no decorative gimmicks,
- safe placement away from important scene content where possible.

The first implementation can use FFmpeg `drawtext` if a suitable local font is
available. If no reliable font is found, the renderer should skip text rendering and
write a warning to the director report rather than failing the whole cut.

### Transitions

Transitions should be purposeful:

- hard cut for high energy and clear beat hits,
- dissolve for slow, calm, visually related shots,
- match cut only when adjacent segments have compatible motion direction and pace.

The renderer must not fake transitions that shorten or damage timing. Any transition
used in `timeline.json` must be representable in the final render or downgraded with
an explicit reason in `director-report.json`.

## Architecture

The director layer should live under new focused modules:

- `aicutting.analysis.motion`: optical-flow, jitter, movement, and rejection scoring.
- `aicutting.analysis.screenshots`: keyframe extraction for agent review and contact sheets.
- `aicutting.director.models`: director-specific reports, decisions, and title suggestions.
- `aicutting.director.engine`: combines analysis, ranking, beat timing, rejection, and title decisions.
- `aicutting.director.location`: metadata-first and agent-assisted title suggestion logic.
- `aicutting.render.titles`: title overlay command construction.

Existing modules remain responsible for their current jobs:

- `aicutting.analysis.video` still discovers/scans candidate windows.
- `aicutting.analysis.audio` still extracts beats and energy.
- `aicutting.planning.engine` may delegate beat-aware decisions to the director layer.
- `aicutting.render.ffmpeg` remains the final renderer.
- `aicutting.pipeline.CutPipeline` remains the shared CLI/GUI entry point.

## Data Flow

1. Discover videos and optional music.
2. Probe media duration, dimensions, and FPS.
3. Build candidate windows across each clip.
4. Score candidate windows for quality and camera movement.
5. Reject bad flight phases and unusable segments.
6. Rank remaining candidates with source diversity and usability.
7. Analyze music beats and energy.
8. Build a beat-aware director timeline.
9. Extract screenshots for selected title/location candidates.
10. Resolve title suggestions through metadata and optional agent review.
11. Render approved overlays and transitions.
12. Write final video and explain all decisions in artifacts.

## Error Handling

The director layer should degrade gracefully.

- If optical flow cannot read a segment, keep the existing quality score and mark
  motion confidence low.
- If too many segments are rejected, fall back to the best non-rejected candidates
  and write a warning.
- If no location confidence is high enough, omit automatic title rendering.
- If an agent backend fails, write the failure into `location-suggestions.json` and
  continue.
- If title rendering fails due to fonts or FFmpeg support, render the video without
  text and report the downgrade.

## Testing Strategy

Tests should be written before implementation and cover:

- smooth synthetic motion scores better than jittery motion,
- abrupt direction changes increase jitter or rejection probability,
- takeoff/landing-like motion is rejected with `takeoff_or_landing_motion`,
- search-flight-like motion is rejected with `search_flight_before_subject`,
- low-confidence location suggestions are not rendered,
- high-confidence location suggestions are attached to the timeline,
- beat-aware planning chooses cuts near beat times,
- hard cuts, dissolves, and downgraded transitions preserve expected duration,
- pipeline writes director and rejection artifacts.

Where possible, tests should use synthetic frames and small generated videos rather
than large fixture media.

## Out of Scope

- perfect landmark recognition,
- online map lookup,
- cloud rendering,
- training a custom vision model,
- replacing DaVinci Resolve,
- manual NLE timeline editing,
- full object detection or semantic segmentation,
- guaranteeing correct place names without metadata or review.

## Definition of Done

This feature is done when AiCutting can analyze real drone clips, reject obvious
takeoff, landing, shaky, and search-flight footage, choose smoother usable segments,
build a beat-aware edit, optionally render high-confidence location titles, and
write explainable artifacts that show why each important segment was selected or
rejected.

The GUI and CLI must still work from the same pipeline. Full verification requires
passing automated tests plus at least one real local preview render showing that the
timeline no longer relies on poor camera movement or blind clip beginnings.
