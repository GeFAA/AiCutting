# AI Drone Director 2.0 Design

## Goal

Build AiCutting 2.0 around a drone-specific AI Director that finds genuinely
usable raw footage moments, cuts them to music with beat intent, and applies
clean motion-aware transitions and animations. The target is not a generic
social-media editor. The target is cinematic drone and travel footage.

## Current Problem

The current pipeline is useful as a foundation but not yet good enough as an
automatic editor. It can still pick weak windows from long raw clips, miss the
actual best moment inside a take, and place cuts that feel disconnected from the
music. Adding flashy transitions on top of this would make bad edits look busy
instead of better.

The 2.0 work therefore starts with director intelligence:

- find stronger sub-segments inside raw drone footage,
- reject more bad motion before planning the timeline,
- understand music structure beyond a flat beat list,
- lock important cuts to musical moments,
- choose transitions only when the source motion supports them.

## Scope

In scope:

- Drone and landscape B-roll only.
- Long raw drone clips with usable and unusable sections mixed together.
- Beat-aware short cinematic edits for travel, real estate, landscape, and
  social reels.
- Local deterministic analysis first, optional local Codex or Claude review
  second.
- FFmpeg-renderable transitions and animations that can be represented in the
  neutral timeline.
- Review artifacts that explain why each shot, cut, and effect was selected.

Out of scope for this 2.0 track:

- Talking-head videos.
- Gaming clips.
- General vlogs.
- Multicam interview editing.
- Cloud-only AI services.
- Full CapCut clone UI.
- Manual timeline editor.

## Design Principles

1. Selection quality comes before effects.
   A beautiful transition between weak shots is still a weak edit.

2. Drone-specific signals beat generic scene detection.
   The director should reason about reveals, approaches, pull-backs, orbits,
   fly-throughs, top-downs, establishing shots, search motion, takeoff, and
   landing motion.

3. Music is structure, not just timestamps.
   The cut plan should use beats, downbeats, phrase boundaries, energy changes,
   and peak sections.

4. Effects are contextual.
   A zoom transition should prefer approach or pull-back motion. A whip blur
   should prefer strong lateral pan. A dissolve should prefer calm establishing
   shots. Flash and impact effects should be reserved for energy peaks.

5. Every decision must be inspectable.
   AiCutting should write artifacts that explain selected shots, rejected shots,
   beat locks, and transition choices.

## AI Director 2.0 Pipeline

The 2.0 pipeline adds four major planning layers before rendering:

1. Shot Intelligence
   Analyze raw footage as many candidate micro-segments, not only fixed windows.
   Score each segment for usability, motion stability, composition, novelty,
   reveal quality, and drone shot type.

2. Music Intelligence
   Convert the music track into a beat grid with section labels, energy curves,
   downbeat guesses, phrase boundaries, and recommended cut densities.

3. Story Timeline Planning
   Build an edit arc from the best shots: establish, develop, peak, release.
   Match clip length and shot type to music energy.

4. Motion-Aware Effects
   Assign transitions, speed ramps, and subtle animation overlays based on
   source motion, target motion, beat position, and edit energy.

## Shot Intelligence

### Candidate Generation

The current fixed-window candidate generation should be extended with a
sub-segment search pass:

- sample long clips at short intervals,
- estimate local stability and motion direction,
- group neighboring high-quality intervals,
- trim weak heads and tails from each candidate,
- keep multiple candidates from one source only when they show different motion
  or visual content.

This prevents a five-second candidate from starting too early during takeoff,
ending during a wobble, or missing the actual reveal moment.

### Drone Shot Types

Each candidate should receive a `shot_type` value:

- `reveal`
- `approach`
- `pull_back`
- `orbit`
- `fly_through`
- `top_down`
- `establishing`
- `tracking`
- `search_motion`
- `takeoff_or_landing`
- `unstable`
- `unknown`

The first implementation can use deterministic CV proxies:

- optical flow direction and magnitude,
- center-weighted composition,
- brightness and contrast stability,
- edge/sharpness consistency,
- horizon or vertical drift proxy,
- object/texture novelty between sampled frames,
- motion smoothness and path efficiency.

Later implementations may add optional local vision-agent review on extracted
contact sheets, but the deterministic scorer remains the default source of
truth.

### Shot Scores

Each candidate should expose a richer score set:

- `technical_score`: sharpness, exposure, contrast, codec/probe sanity.
- `stability_score`: low jitter, no sudden yaw, no vertical shake.
- `composition_score`: useful visual structure, no empty transitional seconds.
- `motion_intent_score`: movement looks intentional rather than searching.
- `reveal_score`: subject or landscape reveal quality.
- `novelty_score`: avoids repetitive near-duplicate shots.
- `drone_director_score`: final weighted score for timeline planning.

Hard rejection remains possible for:

- takeoff or landing motion,
- searching before finding subject,
- excessive yaw or pan instability,
- near-static dead footage when the song requires energy,
- blur or unreadable frames,
- too-short usable interval.

## Music Intelligence

The current audio analysis should become a beat plan:

- `beats_s`: beat timestamps.
- `downbeats_s`: likely strong beats.
- `energy_curve`: normalized energy over time.
- `sections`: intro, build, peak, release, outro.
- `phrase_boundaries_s`: likely 4/8/16 beat boundaries.
- `cut_density`: target cuts per section.

The system should prefer:

- longer clips during intro and calm sections,
- shorter clips during peak sections,
- major shot changes on downbeats or phrase boundaries,
- impact transitions only on high-energy beats,
- subtle dissolves or hard cuts during calm energy.

If no music is provided, the director should still produce a clean cinematic
edit using visual pacing defaults.

## Timeline Planning

The planner should stop choosing clips only by sorted score. It should build a
small edit arc:

1. Establish
   One or two strong establishing, top-down, or wide reveal shots.

2. Move
   Approach, fly-through, tracking, or orbit shots that create momentum.

3. Peak
   Best reveals, fastest clean movement, or most visually impressive shots.

4. Release
   Calm pull-back, establishing, or dissolve-friendly shot.

The planner should also avoid:

- using multiple near-identical shots next to each other,
- using the same source too often unless it has distinct good moments,
- cutting away before a reveal lands,
- starting a selected clip before the usable action begins,
- ending a clip during instability.

## Transitions And Animations

2.0 should add a small high-quality transition library rather than a large
random preset list.

Transition types:

- `hard_cut`: default, especially for beat-locked edits.
- `dissolve`: calm scenic or release moments.
- `smooth_zoom`: approach to approach, pull-back to pull-back, or energy lift.
- `whip_blur`: strong lateral motion match, high-energy sections only.
- `flash_cut`: beat impact or drop accent.
- `speed_ramp`: clean acceleration into or out of a reveal.
- `match_motion`: same direction or similar motion magnitude between shots.

Each transition decision should include:

- selected transition type,
- duration,
- beat anchor,
- source shot type,
- target shot type,
- confidence,
- reason.

The renderer can initially implement these with FFmpeg filters that are stable
and testable. Fancy effects should degrade to hard cuts or dissolves when the
required motion evidence is weak.

## New Artifacts

2.0 should add artifacts that make the director auditable:

- `shot-candidates.json`
  All candidate sub-segments with shot type, scores, and rejection reason.

- `beat-plan.json`
  Beats, energy sections, phrase boundaries, and cut density.

- `story-plan.json`
  The intended edit arc and chosen shots before render-specific details.

- `effect-plan.json`
  Transition and animation decisions with reasons and confidence.

- `director-2-report.json`
  Summary of selected shots, rejected shots, warnings, and quality metrics.

Existing artifacts should continue to be written for compatibility:

- `analysis.json`
- `cut-plan.json`
- `timeline.json`
- `director-report.json`
- `rejected-segments.json`
- `location-suggestions.json`
- `resolve/`

## Desktop Review Experience

The GUI should eventually expose 2.0 decisions in simple language:

- "Selected because: smooth reveal, high sharpness, beat peak."
- "Rejected because: takeoff motion."
- "Cut locked to beat at 12.48s."
- "Transition: smooth zoom because both shots move forward."

The first implementation does not need a full manual editor. It only needs a
review layer that helps non-technical users trust what happened.

## Error Handling

2.0 should fail safely:

- If music analysis fails, show a clear error and suggest replacing the track.
- If beat confidence is low, use visual pacing defaults.
- If transition confidence is low, fall back to hard cut or dissolve.
- If a local agent fails, write the failure into artifacts and continue.
- If FFmpeg cannot render a selected effect, render a simpler fallback and
  report the fallback in `effect-plan.json`.

## Testing Strategy

The implementation must be test-driven. Required coverage:

- synthetic frame sequences for drone shot classification,
- candidate trimming tests that prove bad heads and tails are removed,
- hard rejection tests for takeoff, landing, search motion, and unstable yaw,
- beat-plan tests with synthetic beat and energy fixtures,
- timeline tests proving cuts align to beat targets within tolerance,
- transition selection tests proving effects depend on shot motion and energy,
- FFmpeg command tests for every new renderable effect,
- artifact tests for all new JSON files,
- pipeline integration tests for dry-run and render paths.

Manual verification should include at least one real drone folder:

- run dry-run and inspect `shot-candidates.json`,
- confirm rejected start/landing/search sections,
- inspect `beat-plan.json` for sensible beat targets,
- render a short preview,
- compare selected shots against the raw footage.

## Rollout Plan

The work should be delivered in slices:

1. Shot Intelligence 2.0
   Better drone sub-segment discovery and scoring. This is the highest priority.

2. Beat Plan 2.0
   Stronger music structure and cut target generation.

3. Story Planner 2.0
   Build an edit arc rather than selecting a flat list of top clips.

4. Transition Library 2.0
   Add motion-aware transitions and fallback behavior.

5. Review Artifacts And GUI Surface
   Make decisions inspectable for non-technical users.

## Success Criteria

2.0 is successful when:

- obvious takeoff, landing, and search-flight sections are rarely selected,
- long raw clips contribute their best internal moments, not arbitrary windows,
- cut timing visibly follows the song,
- high-energy sections feel more active than calm sections,
- transitions feel motivated by camera motion and beat energy,
- every automatic decision has a readable artifact reason,
- the project remains testable without cloud services.
