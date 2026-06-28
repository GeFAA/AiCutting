# AiCutting Studio v2 — input selection & live visualisation (plan)

**Date:** 2026-06-28
**Builds on:** `2026-06-28-studio-qml-rework-design.md` (the QML Studio).

## Goal

Three professional upgrades to the QML Studio: (1) real **file/folder selection** (native pickers,
not only drag-drop), (2) a **live, visualised** working view that shows what the AI is doing right
now — the frames it is looking at, the location it found, the shots it kept — instead of a bare
stage bar, and (3) **better options** (output folder, dry-run, tooltips).

## Design

### 1 · Input selection
- **Invite:** keep the drop zone, add a **"Browse folder"** button that opens a native
  `FolderDialog`; the chosen folder runs through the same `backend.setFolder` (so the empty-folder
  guard still applies).
- **Compose / MusicField:** add a **"Choose song"** button opening a native `FileDialog` filtered
  to audio; still droppable.
- **Advanced disclosure (Compose):** an **output folder** override (`FolderDialog`) and a
  **dry-run** toggle ("plan & report only — no render").

### 2 · Live visualisation (the headline)
The pipeline already writes artifacts into the output folder as it runs; the Backend reads them on
each progress event (best-effort) and surfaces them to QML — no pipeline change:

| Stage | What we show | Source artifact |
|------|--------------|-----------------|
| Watch | the location frame + the detected place | `location-screenshots/*.jpg`, `location-suggestions.json` |
| Direct | a strip of the contact-sheet thumbnails the agent is rating, + a determinate `done/total` bar, + "kept X · rejected Y" | `contact-sheets/*.jpg` (+ `ProgressEvent.step/total`), `footage-ratings.json` |
| Cut / Render | a strip of the chosen-clip thumbnails | `report-assets/*.jpg` |

A pure resolver `live_view(phase, output_dir) -> LiveView(hero, thumbnails, detail)` decides what to
show; the Backend exposes `heroImage`, `liveThumbnails`, `liveDetail`, `stepCurrent`, `stepTotal`.
The Working screen renders a determinate sub-bar (when `stepTotal > 0`), the hero image, a thumbnail
strip with the scan-line shimmer, and the detail line — so you literally watch the AI work.

### 3 · Better options
Advanced output + dry-run (above); tooltips on every control; the Invite shows "or **browse**".

## Tasks (TDD; QML verified by offscreen render)

1. **Backend live-view + advanced inputs.** `aicutting/gui/live_view.py`: pure
   `live_view(phase, output_dir) -> LiveView` (best-effort artifact reads, deterministic given the
   dir). Backend gains `heroImage`/`liveThumbnails`/`liveDetail`/`stepCurrent`/`stepTotal`
   properties updated in `_on_progress`, and `startCut` gains `dryRun`/`output`. Unit-test the
   resolver against a tmp dir seeded with each artifact set, and the Backend step wiring.
2. **Native pickers + advanced disclosure (QML).** `FolderDialog` on Invite, `FileDialog` on
   MusicField, an Advanced `Expander` with the output `FolderDialog` + dry-run toggle; wire to
   `backend.setFolder` / `startCut(..., dryRun, output)`. Render-verify Invite + Compose.
3. **Working visualisation (QML).** Determinate sub-bar, `heroImage`, the thumbnail strip with the
   scan-line, and the detail line on the Working screen. Render-verify the Working state with seeded
   live data.
4. **Polish.** Tooltips on pickers/pills/toggles; the headless QML smoke test extended to the new
   controls.

## Out of scope (YAGNI)
Recent-folders history, batch queue, in-app report rendering, settings persistence — post-v2.
