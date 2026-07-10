# LES-L21 — a best-effort `except: return ""` around a reasoned-tier call silently degrades to the floor; bound prompts to the TARGET TIER's limits, and never swallow the failure invisibly

## Aliases

- reasoned distill silently fell back to the deterministic floor
- HTTP 413 "request too large" on the free tier → empty purpose
- unbounded prompt vs free-tier TPM limit
- except: return "" hides the real error
- large repo distills worse than a small one

## Status

validated

## Owner

Chief Architect / Orchestrator (laptop session)

## Evidence

- Recall shakedown (docs/reviews/2026-07-10-recall-shakedown.md): `reason_purpose` built a
  prompt from the README (`_README_CAP_BYTES = 40_000` ≈ 10K tokens) + bounded source files.
  For Recall (38 KB README + 10 files ≈ **18.5K tokens**) Groq's free tier returned
  `HTTP 413 "Request too large … TPM Limit 12000, Requested 17772"`; the rotation pool's
  members all failed → `RuntimeError` → `reason_purpose`'s `except Exception: return ""`
  → the weak deterministic floor. The distill "succeeded" with no error surfaced.
- The reasoned tier itself was fine: the SAME call on a **bounded** prompt (~7K tokens)
  returned an accurate one-sentence purpose. The bug was prompt size × tier limit, hidden by
  a silent fallback.
- A single-provider free pool made it worse: one 413/429 and every member is exhausted;
  a multi-provider pool (Groq/Cerebras/Gemini/Mistral) falls through to a bigger-context member.

## Linked Decisions / Projects

- `packages/aos_core/aos_core/services/distillation.py` — `_bounded_reason_body`, `reason_purpose`, `reason_over_source`
- docs/reviews/2026-07-10-recall-shakedown.md (§3.6, the finding)
- [[LES-L19]] / [[LES-L20]] — sibling routing/tier lessons

## Content

- Event: a quality tier (reasoned distill) silently degraded to the floor for large inputs
  because the prompt exceeded the *free* tier's per-minute token limit, and the failure was
  caught-and-discarded. Hermetic tests never saw it (they run the deterministic tier); only a
  real repo on a real free key exposed it.
- Rules:
  1. **Bound a prompt to the target tier's limits, not to an abstract cap.** A 40K-char README
     is fine for Claude and fatal for a 12K-TPM free model. Size the budget for the *cheapest*
     tier the router might pick (it is now the default), with headroom for system + output.
  2. **Never swallow a reasoned/degradable failure invisibly.** `except: return <fallback>` must
     at least `log.warning` the exception first — otherwise a silent floor looks like success and
     the operator can't tell the good tier failed. Prefer marking the artifact (e.g. a
     `validation_state`) so the degrade is visible downstream, not just in logs.
  3. **Multi-provider pools are resilience, not just cost.** A single free provider means one
     rate-limit/size error floors everything; order the pool so a larger-context member can
     absorb a big prompt.
  4. **Bigger input can mean WORSE output** when a size limit trips a silent fallback — the
     opposite of the intuition. Test the large-input path against the real tier, not just small
     hermetic fixtures.
