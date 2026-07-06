# AOS-SCAN-PRECISION-001 — Scanner precision: manifest/ecosystem breadth + secret-signal fixture awareness

- Status: In Progress
- Owner: laptop session (parallel Orchestrator)
- Branch: `laptop/aos-scanner-precision` (cut from `origin/main` @ `5317dcf`)
- Closes: LES-016 (dotnet/jvm breadth), LES-017 (secret-signal test-fixture awareness). Coordinated: the scanner is free (remote is on the Reuse view; `repository_scanner.py` untouched since AOS-DISTILL-003).

## Verified Baseline (confirmed by inspection)

- `packages/aos_core/aos_core/repository_scanner.py`:
  - `MANIFEST_FILES` (basename → package manager, :50-59) and `MANIFEST_KINDS` (basename → ecosystem kind, :61-76) currently cover **python/node/rust/go only**; `.NET`/`JVM` absent. Matched by exact basename in the file loop (`if name in MANIFEST_FILES` / `if name in MANIFEST_KINDS`, :422-427). `.csproj`/`.sln` are **suffixes** (files like `Api.csproj`), so basename matching cannot catch them — they need suffix-based handling.
  - `ECOSYSTEM_KINDS = {"python","node","rust","go"}` (:123) gates the `MULTIPLE_ECOSYSTEMS` dedup (:516-524).
  - `SECRET_LIKE_FILENAME` (:449-457) emits `severity="warning"` for `name in SECRET_NAMES` (id_rsa, id_dsa, id_ed25519, credentials.json, service-account.json) or `suffix in SECRET_SUFFIXES` (.pem, .key). No path context, so legit test-cert fixtures (e.g. gin `testdata/*.pem`) false-positive (LES-017).
  - `risk_flags` (persisted to `RepositoryDNA.risk_flags`, scan.py:30) contains **warning-severity messages only**; `risk_signals` (full list, in `scan_summary` JSON) carries every signal with severity.
- `tools/pr_guardian.py`: `check_scanner_signals` (:413-466) blocks `scanner-secret-path` on any `SECRET_LIKE_FILENAME` whose `path` is in the PR's changed set — keyed on **code, not severity** (overridable via `PR_GUARDIAN_OVERRIDE_SCANNER`). A separate `SCANNER_MANIFEST_BASENAMES` (:98-110) mirrors the scanner manifest set for an informational `scanner-new-ecosystem` WARN.
- `apps/api/tests/test_scanner.py`: builds fixture repo trees under `tmp_path`, asserts on `manifests`/`package_managers`/`risk_signals` codes/severity.

## Design

### LES-016 — manifest/ecosystem breadth (scanner-only)
- Add JVM **basenames** to `MANIFEST_KINDS` and `MANIFEST_FILES`: `pom.xml`→kind `jvm`/pm `maven`; `build.gradle` + `build.gradle.kts`→kind `jvm`/pm `gradle`.
- Add a **suffix-based manifest map** (new `MANIFEST_SUFFIX_KINDS` / `MANIFEST_SUFFIX_FILES`) for `.NET`: `.csproj`→kind `dotnet`/pm `dotnet`, `.sln`→kind `dotnet`/pm `dotnet`. Extend the file loop (:422-427) to also match suffix-based manifests (mirroring the basename branch; a file counts once).
- Extend `ECOSYSTEM_KINDS` to `{"python","node","rust","go","dotnet","jvm"}` so `MULTIPLE_ECOSYSTEMS` recognizes them. (Rust `Cargo.toml` already covered — LES-016's "likely Rust too" is already handled.)

### LES-017 — secret-signal test-fixture awareness (scanner-only)
- Add `TEST_FIXTURE_DIRS = {"testdata","tests","test","fixtures","__tests__","spec","testfixtures"}` and a helper that returns True if any path component is in that set.
- In the `SECRET_LIKE_FILENAME` branch: if the path is inside a test-fixture dir, emit the signal with `severity="info"` (so it drops out of `risk_flags`/DNA and stops false-flagging test certs); otherwise keep `severity="warning"`. The signal is still emitted (visible in `risk_signals`) — downgraded, not deleted.
- **The guardian's `scanner-secret-path` block is intentionally NOT changed** (it keys on code, is overridable, and is a conscious human-review gate — weakening it would violate "never weaken the guardian"). LES-017 is a scanner *signal-quality* fix.

## In-Scope Files (exact)
- `packages/aos_core/aos_core/repository_scanner.py`
- `apps/api/tests/test_scanner.py`
- `.archetype/work/AOS-SCAN-PRECISION-001.md`
- `knowledge/wiki/lessons/index.md` (mark LES-016 / LES-017 closed) + LES page updates
- `docs/CAPABILITY_MAP.md` (scanner capability note) · `docs/ACTIVE_WORK.md` + `docs/RECENT_CHANGES.md` (own entries — union-safe)

## Out-of-Scope
- `tools/pr_guardian.py` (the secret block stays; the `SCANNER_MANIFEST_BASENAMES` manifest-mirror parity for JVM/.NET is a noted follow-up, not required for correctness — my PR adds no manifest files).
- LES-014 manifest/import architecture edges (separate package).
- `transfer.py`/`distillation.py`/embeddings (remote's zone).
- CURRENT_STATE "Current sprint" line + HANDOFF.

## Acceptance Criteria (assertions, each with evidence)
1. A repo with `Api.csproj`, `pom.xml`, `build.gradle.kts`, and `Cargo.toml` yields `manifests` kinds `{dotnet, jvm, rust}` and `package_managers` including maven/gradle/dotnet. — evidence: `test_scan_detects_dotnet_jvm_rust_ecosystems`.
2. `MULTIPLE_ECOSYSTEMS` fires when dotnet+jvm (or any 2 of the expanded set) co-occur. — evidence: same test asserts the code.
3. A `.pem`/`id_rsa` under `testdata/`/`tests/fixtures/` yields a `SECRET_LIKE_FILENAME` signal at `severity="info"` and NOT in `risk_flags`; the same file outside a fixture dir stays `severity="warning"` and in `risk_flags`. — evidence: `test_secret_like_filename_fixture_aware`.
4. Existing scanner tests still pass unchanged (no regression). — evidence: `pytest apps/api/tests/test_scanner.py`.
5. Full gate green: `ruff check apps/api packages/aos_core apps/worker tools`, `compileall`, `pytest` api+worker; guardian PASS. — evidence: CI + guardian output.

## Verification Plan
- TDD: write the two new tests (RED, they fail on today's scanner) → implement → GREEN.
- Level 2 (local): ruff + compileall + `PYTHONPATH=apps/api:packages/aos_core pytest apps/api/tests -q` (+ worker). Run the scanner on this repo to confirm no change to ArchetypeOS's own self-scan (it has no .NET/JVM manifests).
- Level 3: GitHub CI green on the head SHA → Manual Merge Gate.

## Board Linkage
- Closes LES-016 + LES-017. Plane: create an AOS-SCAN-PRECISION-001 item (In Progress → Done on merge).
