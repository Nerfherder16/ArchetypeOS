# Recall Shakedown — first foreign-project run through the pipeline (2026-07-10)

## 1. Purpose & scope

First end-to-end run of a **real, non-ArchetypeOS project** (System-Recall,
`github.com/Nerfherder16/Recall`) through the intelligence pipeline: register →
scan → DNA → distill (deterministic floor + reasoned tier) → verifier. ArchetypeOS
had only ever audited itself; the per-project machinery (toggle / dispatcher /
per-project heartbeat) and the reasoned-distill routing were **0 live runs on
foreign code**. This shakedown converts "unproven-live" into proven-or-bug-found.

## 2. Method

- **Scan/DNA**: driven through teevee's deployed API (`http://teevee.tail612d5.ts.net:8000`)
  against a `repositories/recall` checkout rsync'd onto the host.
- **Distill (deterministic + reasoned)**: the manual reality harness
  `scripts/reality_test_distillation.py` locally against a scratch sqlite DB +
  `/tmp` scratch vault, so nothing touched the git tree.
- **Reasoned tier**: `LLM_PROVIDER=claude_code` (bypasses the deterministic
  short-circuit) + a Groq free-tier key → `route("distillation", PUBLIC)` → FREE.
- Operator is ground truth (Tim knows Recall cold).

## 3. Findings

### ✅ 3.1 Scan is accurate on foreign code
`frameworks = [fastapi, pydantic, react]`; `languages = {Python 462, TS-React 86,
Markdown 40, JS 39, TS 26, …}`; `package_managers = [npm, python]`. All correct.
The scan half of the pipeline works on a repo that is not ArchetypeOS.

### ✅ 3.2 The reasoned distill produces an accurate purpose (on bounded input)
Free-tier (llama-3.3-70b) returned valid JSON and:
> "This repository provides a neuroscience-inspired persistent memory system for
> AI coding assistants, enabling them to learn from experience and retain knowledge
> across sessions."
Spot-on for Recall. The reasoned quality tier is real and good — when the prompt fits.

### ✅ 3.3 The #49 tier fix is live in production
`route("distillation") → FREE_HOSTED → provider "rotating"`, Groq answered, and the
pool now stamps `"rotating"` on the result so the ledger tiers it FREE (was `local`).

### ✅ 3.4 teevee SSH established (repeatable)
teevee = `100.123.29.114`, WSL2 Ubuntu, **Tailscale SSH** (`trg16@teevee.tail612d5.ts.net`,
no keys/passwords to manage). Documented in the network map.

### 🐛 3.5 The deployed API cannot distill (read-only vault)
`POST /repositories/{id}/distill` → **409**: the compose stack mounts the knowledge
vault `:ro`. teevee produces **DNA**, not **distilled knowledge**. Distillation must
run from a **writable** checkout, then the committed vault is synced back. See the
Operating-Model Decision (§4).

### 🐛 3.6 The distill prompt is unbounded vs tier limits → silent floor
Recall's reasoned prompt was **~18,481 tokens** (38 KB README + 10 source files).
Groq free tier rejected it: `HTTP 413 — "Request too large … TPM Limit 12000,
Requested 17772."` All (single, local) pool members failed → `RuntimeError` →
`reason_purpose`'s `except: return ""` **silently** fell back to the weak
deterministic floor. With free-tier routing now the default, any repo with a large
README + source silently loses the reasoned summary, and nobody is told.
Tracked as **task #50**. Fix: (a) bound the prompt to a tier-safe token budget;
(b) fall through to a larger-context pool member on 413 (order the pool by capacity —
teevee's 4-provider pool with Gemini/Cerebras would have survived this); (c) stop
swallowing the error — log/mark the reasoned-tier failure.

## 4. Operating-model decision (deployed distillation)

**Decision: distillation stays a local-first, build-time activity; the deployed
instance is read-only and consumes the synced vault. We do NOT give the deployed
container a writable git vault.**

Rationale (Engineering Constitution — local-first, vault = git source of truth):
- The knowledge vault is git-tracked; the deployed API mounting it `:ro` is correct
  (a service should not mutate the source-of-truth working tree — drift/no-review risk).
- Intended flow: **distill on a writable checkout → commit the vault page → deployed
  instance `sync_knowledge` reads it into `KnowledgePage` rows.** The 409 is the
  system correctly refusing to violate this.
- Gap to close (follow-up, not this PR): there must be a *mechanism* that actually
  runs the local distill + commit for onboarded repos, or the deployed knowledge never
  grows. Recommended: a **distill dispatcher** mirroring the per-project coherence
  dispatcher — iterate onboarded repos on a writable checkout, distill, commit the
  vault pages, push (review-gated). Do NOT bolt on-demand distillation onto the
  read-only deployed API.
- If on-demand distillation from the deployed UI is ever wanted, it writes to a
  separate **writable derived store** (not the git vault), kept distinct from the
  source-of-truth vault — a deliberate future feature, not a config loosening.

## 5. Verdict

The intelligence loop **connects end-to-end on foreign code** — scan, DNA, and
reasoned distill each work in isolation, and the reasoned output is genuinely
accurate. Two integration seams break under real-world conditions (deployed vault
read-only; free-tier token limits with silent fallback). That is a healthy first
result: the platform is real, with specific, fixable rough edges — not a mirage.

## 6. Follow-ups
- **#50** — bound the distill prompt to tier limits + stop the silent floor fallback (highest value; directly hardens the routing).
- **§4 mechanism** — a distill dispatcher (writable-checkout, commit, review-gated) so deployed knowledge grows.
- Housekeeping — the shakedown left a `Recall` project + repo row + a 23 MB `repositories/recall` checkout on teevee (test artifacts).
