# claude-video

## Aliases

- bradautomates/claude-video
- /watch skill
- Claude video comprehension

## Status

evaluated

## Verdict

partial-borrow (greenlit 2026-07-09) — adopt the video pipeline as an AOS **video-ingestion capability**. An operator or another system feeds ArchetypeOS a video URL about a topic of interest; AOS downloads, extracts frames, transcribes, and returns a structured breakdown (transcript, key frames, summary). Cloud transcription (Groq/OpenAI) is explicitly accepted by the operator. This is an ingestion/enrichment capability feeding the Research Engine and Knowledge Vault, exposed so other systems can call it — not just a Claude Code slash command.

> Reassessment note: the initial teardown scored this `reject/monitor` on a local-first + "video is peripheral" reading. The operator overrode both: cloud is acceptable, and "URL in → structured breakdown out" is a wanted product capability. Verdict upgraded accordingly.

## Repo facts

- URL: https://github.com/bradautomates/claude-video
- Language: Python · License: MIT · Stars: ~6,213 · Last push: 2026-07-01
- Shape: Claude Code plugin exposing a `/watch` slash command. Pipeline: download (yt-dlp) → optional frame extraction (ffmpeg) → transcription → hand artifacts to Claude.

## AOS engines touched

- Research Engine (overlap: medium — video as an evidence source it can't currently ingest)
- Architecture Studio (overlap: low — frame extraction from walkthroughs; weak use case)
- Design Intelligence (overlap: low — UI walkthrough references; weak use case)
- Knowledge Vault (overlap: low — transcripts as notes)

## Overlap vs additive

- Additive (greenlit): the full **download → frame-extraction → transcription** pipeline, wrapped as an AOS video-ingestion worker/endpoint (URL in → structured breakdown out). Feeds the Research Engine and Knowledge Vault; callable by other systems the operator builds. Captions path (`--skip-download`) stays the cheap default; cloud Whisper (Groq/OpenAI) is the fallback for non-captioned video.
- Defer (revisit after base capability ships): deep Architecture Studio diagram-from-frames and Design Intelligence UI-reference extraction — lower value, build once the ingestion spine exists.

## Risks

- **Transcription is cloud-only** (confirmed in `whisper.py`: Groq `api.groq.com` / OpenAI `api.openai.com`; no local Whisper path). Operator accepts cloud transcription (2026-07-09), so this is no longer a blocker — but the ingestion capability must log per-call cost and note that video URLs/audio leave the local network. A local Whisper backend can be added later if local-first is reinstated for this path.
- Prompt injection via untrusted transcript text injected verbatim into Claude context — treat transcript as data/evidence, never instructions; restrict to known engineering channels.
- Bus factor of 1; yt-dlp ToS/legal gray area (mitigated by the captions-only `--skip-download` path).
- Heavy binary deps (ffmpeg, yt-dlp, whisper models) if the full pipeline enters the AOS container stack.
- MIT license — compatible; attribution required if code is vendored.

## Evidence

- [[../../../docs/repo-research/claude-video|Full teardown]] — file inventory, pipeline trace, dependency + privacy audit, integration options
- Transcription backend confirmed cloud-only in `whisper.py` (Groq/OpenAI)

## Linked Decisions / Projects

- Plane AOS-61 — "Evaluate: claude-video" (Done) — in the External Repo Evaluation & Adoption Pipeline module
- Plane AOS-62 — "Adopt claude-video pipeline as AOS video-ingestion capability" (Todo / open, RFC-first) — greenlit 2026-07-09
