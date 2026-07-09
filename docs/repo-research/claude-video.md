# Repo Research: bradautomates/claude-video

**Analyzed:** 2026-07-09
**Stack:** Python (pure stdlib), ffmpeg, yt-dlp, Groq API / OpenAI API (optional, cloud)
**Activity:** Active — v0.2.0 released 2026-06-29, last commit 2026-06-30 (bug fix)
**License:** MIT
**Stars:** ~6.2K

---

## Verdict

claude-video is a Claude Code skill (slash command `/watch`) that lets an AI agent "watch" any video by downloading it with yt-dlp, extracting frames as JPEGs via ffmpeg, pulling a timestamped transcript from native captions or a cloud Whisper API, then printing all of that to stdout so Claude can `Read` the frame paths and answer questions about the video. It is consumer/developer tooling aimed at individual productivity — summarizing YouTube videos, diagnosing bug recordings, turning tutorial playlists into notes. The codebase is mature, clean, well-tested, and actively maintained by a single author. It is **not** an engineering intelligence tool; it is a multimodal ingestion adapter.

---

## Architecture

```
User invokes: /watch <url-or-path> [question]
       |
       v
  SKILL.md (Claude reads this to understand what to do)
       |
       v
  Claude runs: python3 ${SKILL_DIR}/scripts/setup.py --check
       |
       v
  Claude runs: python3 ${SKILL_DIR}/scripts/watch.py <source> [flags]
       |
       +---> download.py       -- yt-dlp wrapper: fetch_captions() first (free, no download),
       |                          then download() if frames/audio needed. Outputs video file + .vtt
       |
       +---> frames.py         -- ffmpeg frame extraction: 3 strategies:
       |                          extract_keyframes() / extract_scene_or_uniform() / extract()
       |                          + dedup pass (16x16 grayscale thumbnails, MAD threshold)
       |                          + even-sample to cap + transcript-cue pinning
       |
       +---> transcribe.py     -- parse .vtt to [{start, end, text}], dedupe rolling YT auto-subs
       |
       +---> whisper.py        -- if no captions: ffmpeg extracts mono 16kHz mp3,
       |                          uploads to api.groq.com OR api.openai.com Whisper endpoint
       |                          (pure stdlib urllib, multipart, chunked for >24MB audio)
       |
       v
  watch.py prints markdown report to stdout:
    - metadata (title, uploader, duration, resolution)
    - list of frame file paths with t=MM:SS timestamp + reason tag
    - full timestamped transcript block
    - working directory path for cleanup
       |
       v
  Claude Reads each frame path (parallel tool calls) -> multimodal context
  Claude synthesizes answer from frames + transcript
```

### Packaging model

The skill ships as a self-contained folder `skills/watch/` containing `SKILL.md` and `scripts/`. This folder is copied atomically by the Agent Skills CLI (`npx skills add`), installed via Claude Code's plugin marketplace, or uploaded to claude.ai as a `.skill` bundle (zip). The `SKILL.md` frontmatter declares `name: watch`, `user-invocable: true`, and `allowed-tools: Bash, Read, AskUserQuestion`.

There is no MCP server, no daemon, no persistent process. The pipeline is synchronous shell-outs: one yt-dlp call, one-to-several ffmpeg calls, an optional HTTPS POST to a cloud Whisper endpoint.

---

## File Inventory

```
.
├── skills/watch/                      # Self-contained skill unit
│   ├── SKILL.md                       # Canonical skill contract: instructions to Claude, all flags
│   └── scripts/
│       ├── watch.py                   # Entry point: orchestrates all stages, prints markdown report
│       ├── download.py                # yt-dlp wrapper: fetch_captions (no-download), download_url
│       ├── frames.py                  # ffmpeg extraction: keyframe, scene, uniform; dedup; auto-fps
│       ├── transcribe.py              # VTT parser + rolling-duplicate deduplication
│       ├── whisper.py                 # Groq/OpenAI Whisper clients (stdlib urllib, chunked upload)
│       ├── config.py                  # ~/.config/watch/.env reader; detail mode -> frame_cap()
│       ├── setup.py                   # Preflight (--check, --json), binary installer, .env scaffolding
│       └── build-skill.sh             # Packages dist/watch.skill for claude.ai upload
├── hooks/
│   ├── hooks.json                     # SessionStart hook: runs check-setup.sh in <5s
│   └── scripts/check-setup.sh        # One-liner status display in Claude Code sessions
├── .claude-plugin/
│   ├── plugin.json                    # Claude Code plugin manifest: name, version, description
│   └── marketplace.json              # Marketplace listing
├── .codex-plugin/plugin.json          # Codex/agents manifest: "skills": "./skills/"
├── .agents/plugins/marketplace.json   # Agent Skills marketplace listing
├── tests/
│   ├── conftest.py                    # Fixtures: ffmpeg-synthesized short video clips (no network)
│   ├── test_config.py                 # config.py: env parsing, inline-comment stripping
│   ├── test_dedup.py                  # frames.py: perceptual dedup, threshold, fail-open
│   ├── test_download.py               # download.py: URL detection, local path resolution
│   ├── test_fixtures.py               # conftest fixture smoke tests
│   ├── test_frames.py                 # auto_fps, auto_fps_focus, extract
│   ├── test_setup.py                  # setup.py preflight output
│   ├── test_timestamps.py             # --timestamps flag: cue extraction, window dropping
│   ├── test_watch.py                  # watch.py integration: argparse, report format
│   └── test_whisper.py                # plan_chunks, shift_segments, _build_multipart
├── AGENTS.md                          # Generic-agent entry point (forwarded from CLAUDE.md)
├── CHANGELOG.md                       # Version history (v0.1.0 -> v0.2.0)
└── dev-sync.sh                        # Dev utility: mirror working tree into installed plugin cache
```

---

## Key Capabilities

**1. Captions-first, download-optional pipeline.** `download.py:fetch_captions()` calls yt-dlp with `--skip-download` first. If native captions exist (YouTube manual or auto-generated subs), the entire pipeline returns without downloading any video — free, fast (~4.5s for a 49-minute video), no GPU needed.

**2. Three frame-extraction strategies with automatic fallback.**
- `efficient`: `ffmpeg -skip_frame nokey` — decodes only keyframes, near-instant (~0.5s).
- `balanced`/`token-burner`: `ffmpeg select='eq(n,0)+gt(scene,0.20)'` — scene-change detection, full decode. Falls back to uniform sampling if fewer than 8 scene cuts detected.
- Uniform: `ffmpeg -vf fps=N` — deterministic, always available.

**3. Perceptual dedup in pure stdlib.** `frames.py:dedupe_perceptual()` runs one ffmpeg call to downscale all extracted JPEGs to 16x16 grayscale raw pixels, then computes mean absolute difference between consecutive kept frames. No Pillow, no numpy. Threshold 2.0/255 is deliberately conservative — a single changed line of code in a terminal frame survives.

**4. Cloud Whisper via pure stdlib urllib.** `whisper.py` builds multipart/form-data by hand (no `requests`, no vendor SDK), posts to `api.groq.com/openai/v1/audio/transcriptions` or `api.openai.com/v1/audio/transcriptions`, and handles 429 rate-limit retry with exponential backoff. Long audio is chunked at 24MB, transcribed per-chunk, and timestamps are shifted back into source time.

**5. Transcript-cue frame pinning.** `--timestamps T1,T2,...` extracts frames at presenter-flagged moments ("look here", "as you can see"). These are pinned before the detail engine runs so they are never evicted by the even-sampling cap. The `merge_frames()` function merges cue frames and detail frames in chronological order.

**6. Harness-agnostic design.** SKILL.md resolves `SKILL_DIR` from the directory of the file Claude read, not from an env var. This makes the skill work identically in Claude Code, Codex, Cursor, Gemini CLI, and claude.ai web.

---

## Notable Patterns (worth borrowing)

| Pattern | Where | Why it's useful |
|---------|-------|-----------------|
| Captions-first fallback chain: free native captions -> cloud Whisper -> frames-only | `watch.py` lines 84-106, 175-205 | Degrades gracefully; avoids paid API calls for the common case |
| Token-budget-by-duration auto-fps | `frames.py:auto_fps()` lines 128-152 | Keeps context cost predictable regardless of video length |
| Pure-stdlib multipart upload | `whisper.py:_build_multipart()` lines 165-190 | Zero pip dependencies for API calls; useful for any agent skill that must be self-contained |
| Even-sample with first+last guarantee | `frames.py:_even_indices()` + `_even_sample()` | Ensures temporal coverage never drops the clip's tail, regardless of cap |
| Chunked audio upload with timestamp offset | `whisper.py:plan_chunks()` + `transcribe_chunks()` + `shift_segments()` | Handles large audio without special-casing; graceful partial failure |
| Perceptual dedup via one ffmpeg rawvideo call | `frames.py:_thumb_frames()` + `dedupe_perceptual()` | No image libraries; one subprocess call amortizes over all frames |
| SessionStart hook for sub-100ms preflight | `hooks/hooks.json` + `hooks/scripts/check-setup.sh` | Silent on success, visible on first run — low friction setup UX |
| Self-contained skill packaging with sibling scripts | `AGENTS.md` orientation section | Enables `npx install` to copy a working unit; no harness env vars needed |

---

## Risks / Rough Edges

**1. Transcription is cloud-only. This conflicts with AOS's local-first principle.**
Confirmed in `whisper.py:GROQ_ENDPOINT` and `OPENAI_ENDPOINT`. There is no local Whisper path — no whisper.cpp, no faster-whisper, no local model. When a video has no native captions, audio is uploaded to `api.groq.com` or `api.openai.com`. For AOS, which handles potentially proprietary architecture diagrams, internal engineering talks, or screen recordings of production systems, this is a material privacy concern. The `--no-whisper` flag disables the cloud call but also eliminates transcription entirely.

**2. Bus factor is 1.**
Single author (`bradautomates` / Bradley Bonanno). The repo is well-structured and has tests, but there are no other contributors visible in the commit history. High star count reflects discovery velocity, not community depth.

**3. yt-dlp ToS/legal exposure.**
Downloading arbitrary video from YouTube, TikTok, Instagram, etc. raises platform ToS issues. For AOS's primary engineering-intelligence use cases (conference talks from official channels, vendor tutorials, architecture walkthroughs), the risk is lower than for consumer media, but it is not zero. `download.py:fetch_captions()` uses `--skip-download` for the captioned path, which mitigates this for the majority of public engineering content.

**4. Heavy binary dependency chain.**
Requires `ffmpeg`/`ffprobe` + `yt-dlp` on the PATH in whatever execution environment calls the skill. In a containerized AOS deployment this means these binaries must be present in the worker container. They add significant image size (ffmpeg static build is ~60-100MB). No Python packages are required beyond stdlib.

**5. Disk footprint is unbounded per invocation.**
The working directory under `/tmp` holds the downloaded video (up to several GB for long 4K content), all extracted JPEG frames, and the audio file. The SKILL.md instructs Claude to `rm -rf` it when done, but this is a model-issued shell command, not a guaranteed cleanup. In an AOS worker container running many parallel jobs, this could exhaust disk.

**6. Prompt injection via untrusted transcript content.**
The transcript is injected verbatim into Claude's context as a fenced code block. A malicious video could embed instruction-injection in its subtitles or spoken audio. The risk is real for any public video ingestion pipeline. AOS already faces this risk in its Research Engine (web content), but video transcripts add a new attack surface since the content is less predictable than structured docs.

**7. Frame token cost is significant.**
At 512px width, each frame costs ~197 image tokens. 100 frames (default `balanced` cap) = ~20k image tokens per `/watch` call. AOS already pays substantial context costs for its research and architecture-analysis tasks. Stacking 20k image tokens per video reference would escalate per-job cost materially.

**8. No local-video-only mode without yt-dlp.**
Even for a local `.mp4` file, the setup preflight checks for `yt-dlp` on the PATH. `download.py:resolve_local()` does not actually call yt-dlp for local paths, but the setup script will warn/fail if it's absent. This is a minor friction point for a worker container that only needs local file processing.

---

## Integration Fit with ArchetypeOS

### Honest framing

claude-video is an **ingestion adapter**. It does not reason, rank evidence, evaluate fitness, or make recommendations. It converts a video URL or file into (frames + transcript) and hands the raw content to Claude. The intelligence work is entirely Claude's. In an AOS context, the question is whether video is a meaningful **evidence source** for the Research Engine, Architecture Studio, Design Intelligence, or Knowledge Vault.

### Research Engine

**Potentially additive, but narrow.** The Research Engine finds and ranks evidence from documentation, reference implementations, benchmarks, and community discussion. Conference talks (GOTO, QCon, Strange Loop, Kubecon) are a legitimate engineering-evidence source: a 40-minute architecture walkthrough by a tech lead contains information not captured in any doc or repo. The `transcript` mode (captions-only, no download, free) makes this cost-viable for captioned YouTube content. However:
- Video transcripts are unstructured, verbose, and poorly ranked evidence compared to authored docs or benchmarks.
- The Research Engine would need to treat transcripts as raw ingestion input, not ranked evidence — requiring additional summarization and citation extraction before they are useful.
- The frame content (slides, diagrams on screen) adds genuine value that transcripts alone cannot, but at ~20k image tokens per video this is expensive for a background research job.
- The local-first conflict (cloud Whisper for non-captioned content) limits this to videos with native captions, or requires accepting the cloud call for select high-value content.

**Verdict for Research Engine:** Additive but not core. The `transcript` mode (captions path only) is the only privacy-safe route. That covers most major conference talks on YouTube. Useful as an optional evidence source, not a required capability.

### Architecture Studio

**Marginal fit.** Architecture Studio creates editable architecture models from repositories, text, diagrams, and uploaded images. Video frames of whiteboard sessions or diagram walkthroughs could theoretically feed this. In practice:
- Whiteboard diagrams captured as video frames are low-fidelity compared to uploaded images.
- The value of a video walkthrough is in the narration explaining the diagram, not the frame itself — which brings it back to the transcript.
- Architecture Studio already accepts uploaded images. A user can screenshot a video frame and upload it directly without running the full video pipeline.
- There is no structured output from claude-video that Architecture Studio could consume programmatically — it produces a markdown report for Claude to read, not a machine-parseable artifact.

**Verdict for Architecture Studio:** Out of scope for programmatic integration. The "extract a diagram from a video" use case is better served by the user taking a screenshot.

### Design Intelligence

**Marginal fit.** Design Intelligence recommends UI styles and components. UI walkthrough videos could in theory serve as design references. But:
- The resolution cap (512px default, 1024px max) is marginal for UI detail.
- A designer would use screenshots or Figma files, not video frames.
- AOS already has Figma MCP integration.

**Verdict for Design Intelligence:** Out of scope. Not additive over existing Figma integration.

### Knowledge Vault / Research Notes

**Most plausible integration point.** AOS has an Obsidian layer and a research-notes system. Video transcripts (especially from conference talks or vendor architecture sessions) could become knowledge vault entries. The workflow would be:
1. Research Librarian agent runs `/watch <url> --detail transcript` (captions-only, free, local).
2. Claude summarizes the transcript into a structured note.
3. Note is written to the knowledge vault with source attribution.

This is the least privacy-risky integration path (captions-only, no cloud Whisper call, no video download). It is also the most operationally straightforward: the transcript pipeline is a single yt-dlp call and a VTT parse.

**Verdict for Knowledge Vault:** Additive and viable — but only the `transcript` (captions-only) mode. This is the most natural integration point.

---

## Integration Options

### Option A: Vendor the skill as-is (install as Claude Code plugin)

**What:** Install `bradautomates/claude-video` via `/plugin install watch@claude-video` in AOS's Claude Code sessions. Agents can invoke `/watch` ad hoc when they encounter a video URL in research.

**Effort:** Near-zero. One install command.
**Risk:** Low for occasional use; medium for systematic use (disk, token cost, cloud Whisper).
**Local-first:** Partial — captions path is local; Whisper fallback is cloud. Set `--no-whisper` and accept transcription gaps for non-captioned content.
**Coupling:** None — installed as an isolated skill, no AOS code changes.
**AOS gain:** Unblocks ad-hoc video analysis during research sessions. Agents can process conference talks without manual intervention.
**Limitations:** No programmatic output format; outputs a markdown report Claude reads, not a structured artifact AOS can index. Not suitable for batch research jobs.

### Option B: Borrow only the captions+transcript pipeline as a worker-container capability

**What:** Extract `download.py:fetch_captions()` + `transcribe.py:parse_vtt()` + `transcribe.py:format_transcript()` into an AOS Research Worker microservice. Given MIT license, this is straightforward. The three files total ~8KB of pure-stdlib Python with no external packages beyond yt-dlp.

**Effort:** Low (1-2 days). Add yt-dlp to a worker container, write a thin FastAPI endpoint that accepts a URL, calls fetch_captions, parses the VTT, and returns `{transcript: str, segments: [{start, end, text}], source: str}`. The Research Engine can call this when it encounters a video URL.

**Risk:** Low. No cloud API calls on the captions path. yt-dlp ToS risk is present but manageable for engineering-content sources.
**Local-first:** Fully local on the captions path. Explicitly exclude Whisper.
**Coupling:** Adds yt-dlp binary to one worker container. Clean boundary: the worker provides a structured transcript, not a Claude context injection.
**AOS gain:** Research Engine can ingest engineering conference talks and tutorial videos as structured text evidence, without needing Claude to see frames. This is the highest-value, lowest-cost, most privacy-safe integration.

### Option C: Borrow the frame-extraction pipeline for Architecture Studio image inputs

**What:** Extract `frames.py` (the ffmpeg wrapper) as a standalone utility in a worker container. Accept a local video path or downloaded file, return paths to extracted frames. Architecture Studio or Design Intelligence can use frames as image inputs.

**Effort:** Medium (2-3 days). Containerize with ffmpeg, write FastAPI endpoint, integrate with Architecture Studio's image-input surface.
**Risk:** Medium. Frame extraction is local (no cloud calls), but disk footprint and frame token cost are significant. The use case (extracting architecture diagrams from video) is weak.
**Local-first:** Fully local.
**Coupling:** Adds ffmpeg to a worker container (may already be present if AOS does any media work). Adds integration surface between frame extractor and Architecture Studio.
**AOS gain:** Marginal. The primary value would be in diagram extraction from screen-capture recordings, which is a niche use case. Users can take screenshots instead.
**Recommendation:** Do not pursue unless there is a confirmed, recurring user need for this specific workflow.

### Option D: Reject integration — treat video as out of scope

**What:** Accept that video ingestion is not a core engineering-intelligence capability for AOS. Note the tool in the register for ad-hoc use but do not integrate it into any AOS subsystem.

**Effort:** Zero.
**Risk:** None.
**Local-first:** N/A.
**Coupling:** None.
**AOS gain:** None direct. Keeps AOS's dependency surface clean.
**When to choose:** If the Research Engine's evidence sources already cover the engineering-content landscape adequately (docs, repos, issues, benchmarks), and video is a marginal addition that doesn't justify the operational overhead.

---

## Recommendation

### Summary

Video ingestion is **peripheral, not core**, to an engineering intelligence platform. The reasoning is this: AOS's governing principle is "evidence over opinion" and "verification over inference." A video transcript is weak evidence — it is unverified, unstructured, and requires additional processing to become ranked evidence. The real value of engineering talks is almost always captured in the speaker's slides, which are typically published separately, or in associated blog posts, docs, and repos that the Research Engine can already ingest. Video adds marginal incremental value at non-trivial cost (token budget, disk, binary deps, cloud Whisper for non-captioned content).

**Verdict: partial-borrow.** The captions/transcript pipeline (Option B) is worth extracting as a lightweight Research Worker capability. The full skill (Option A) is acceptable for ad-hoc use. Frame extraction (Option C) and full integration are out of scope.

### Evidence

- Confirmed in code: transcription is **cloud-only** (Groq or OpenAI Whisper API) when native captions are absent. `whisper.py:GROQ_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"` — no local path exists.
- The captions-only path (`fetch_captions()` in `download.py`) is fully local: one yt-dlp `--skip-download` call, no binary upload, no API key required. This covers the majority of YouTube engineering content.
- Token cost per video: ~20k image tokens for 100 frames at 512px (`balanced` mode, per README benchmark). At AOS's scale this is significant.
- The skill produces a markdown report for Claude to read, not a structured artifact. No programmatic output interface exists.
- MIT license confirmed in `LICENSE` file — no attribution constraint beyond credit.

### Recommendation

**For immediate adoption:** Install the skill via `/plugin install watch@claude-video` in Claude Code sessions (Option A). Cost: one command. Risk: low. Useful for Research Librarian agents that encounter video URLs during ad-hoc research. Set `WATCH_DETAIL=transcript` in `~/.config/watch/.env` to default to the captions-only mode, and add `--no-whisper` to any automated invocations to prevent cloud audio uploads.

**For medium-term investigation:** Evaluate whether the Research Engine's evidence ingestion pipeline would benefit from a structured transcript service (Option B). If the Research Engine is processing engineering conference talks at scale, the yt-dlp + VTT pipeline is trivial to run in a worker container and adds a genuinely new evidence source. Implementation cost is 1-2 days.

**Do not pursue:** Full frame extraction integration for Architecture Studio or Design Intelligence (Option C). The use case is weak and the cost-to-value ratio is poor.

### Alternatives Considered

- **Use a local Whisper model instead.** faster-whisper or whisper.cpp could replace the cloud Whisper call and resolve the local-first conflict. However, this would require maintaining a local model (several GB) and GPU/CPU resources for inference. This is a capability AOS may want to build independently, not tied to this skill.
- **Use YouTube's data API for transcripts.** The YouTube Data API v3 provides captions and transcripts directly. This avoids yt-dlp entirely and has clearer ToS standing. However, it requires OAuth and only covers YouTube (not Vimeo, Loom, etc.). Worth evaluating as an alternative to yt-dlp for the narrow YouTube-only case.
- **Ignore video entirely.** Reasonable for v1 of AOS. Engineering content is well-served by docs, repos, and benchmarks. Video can be deferred to a later capability iteration.

### Pros

- The captions-only path is fully local, free, and fast.
- Pure-stdlib Python — no pip packages, easy to containerize.
- MIT license — no restrictions on use or modification.
- Well-tested code (10 test modules, ffmpeg-synthesized fixtures, no network required).
- Active maintenance by a responsive author (commits within 9 days of analysis date).
- The transcript output format (`[MM:SS] text`) is clean and directly ingestable.

### Cons

- Transcription fallback (Whisper) is cloud-only — conflicts with local-first principle for non-captioned content.
- Video is a weak evidence source for an engineering intelligence platform; the information it adds is mostly recoverable from associated docs.
- Binary dependencies (ffmpeg, yt-dlp) add container bloat.
- No structured programmatic output — the skill is designed for Claude to read, not for AOS to index.
- Single-author bus factor.
- yt-dlp ToS risk for platform-downloaded content.
- Per-invocation disk footprint is unbounded (video + frames + audio in /tmp).

### Risk

**Local-first risk:** HIGH if Whisper fallback is enabled. LOW if `--no-whisper` is enforced and only native-captioned content is processed.
**Privacy risk:** LOW on captions path (no data leaves the machine). MEDIUM if Whisper is enabled (audio of potentially proprietary recordings is uploaded to a cloud API).
**Prompt injection:** MEDIUM. Video transcripts from untrusted sources could contain instruction injections. Mitigate by treating transcripts as raw text evidence (not instructions) in the Research Engine pipeline, and by sourcing only from known engineering content channels.
**Operational risk:** LOW for ad-hoc use. MEDIUM for systematic batch use (disk, token cost, yt-dlp rate limits).

### Effort

- Option A (install as-is): < 1 hour.
- Option B (extract captions pipeline): 1-2 days including containerization and FastAPI endpoint.
- Option C (frame pipeline integration): 3-5 days including Architecture Studio integration; not recommended.

### Dependencies

- `yt-dlp` binary in worker container (for any integration option).
- `ffmpeg`/`ffprobe` binaries (for frame extraction only; not needed for captions-only path).
- `GROQ_API_KEY` or `OPENAI_API_KEY` (only if Whisper fallback is enabled — not recommended for AOS).
- Python 3.8+ (pure stdlib; no additional packages).

### Acceptance Criteria

If Option B (captions pipeline service) is pursued:
- Worker container accepts a video URL, returns `{transcript: str, segments: [{start, end, text}], source: "captions" | "none"}`.
- No audio is uploaded to any cloud API.
- Service handles URLs with no captions gracefully (returns `source: "none"`, empty segments).
- Research Engine can call the service and ingest the transcript as an evidence source with citation to the original URL.
- yt-dlp ToS risk is documented and accepted in AOS's risk register for engineering-content sources.

### Next Steps

1. Install the skill ad-hoc (`/plugin install watch@claude-video`) and configure `WATCH_DETAIL=transcript` + `--no-whisper` as defaults. Use it opportunistically in Research Librarian sessions.
2. Track whether Research Librarian agents encounter video URLs frequently enough to justify a systematic transcript ingestion service. If yes, implement Option B.
3. Evaluate local Whisper (faster-whisper or whisper.cpp) independently of this skill, as a general AOS capability for transcribing local recordings (screen captures, meeting recordings). This is orthogonal to claude-video and worth pursuing on its own merits.
4. Do not schedule Architecture Studio or Design Intelligence integration.

---

## Transcription: Local vs. Cloud — Explicit Answer

**Cloud-only.** Confirmed in source code:
- `whisper.py:GROQ_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"` (line 24)
- `whisper.py:OPENAI_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"` (line 27)
- There is no code path for local model inference anywhere in the repository.
- The free path (no cloud calls) is native captions via yt-dlp `--skip-download`. This covers most YouTube engineering content.
- `--no-whisper` flag disables the fallback; set this flag for all AOS-automated invocations.

**Local-first implication:** AOS can use claude-video safely for captioned content with `--no-whisper`. For non-captioned content (local recordings, some Vimeo, TikTok), transcription requires either a cloud API call (violates local-first for sensitive content) or local Whisper infrastructure (not provided by this tool — would need to be built separately).
