## Layer 3: Architecture and Modeling

Owns system structure.

Capabilities:

- Architecture Studio
- Architecture Spine Graph (AOS-ARCH-SEMANTICS-001: beyond directory `contains` edges, the scanner now parses detected Docker Compose files into `service` nodes and `depends_on` edges — both the list form `depends_on: [db, redis]` and the map form `depends_on: {db: {condition: ...}}` — persisted through the generic node/edge path and surfaced in `RepositoryDNA.runtime_services`; parsing is tolerant, so a missing/malformed/non-mapping compose adds a note and never raises. LES-014 compose/service half. **The manifest/dependency half shipped (AOS-ARCH-EDGES-001):** the scanner wires the dormant `_LOCAL_DEP_PARSERS` — `requirements.txt` `-e ./`, `pyproject.toml` poetry/uv `path=`, `package.json` `file:`/`link:`, `go.mod` `replace => ./` — into top-level-granularity `depends_on` edges resolved relative to each manifest's dir, deduped/bounded (`MAX_LOCAL_DEP_EDGES`)/tolerant, with manifest-provenance evidence. Source `import`-graph edges remain a separate follow-up)
- Framework detection from manifest bodies (AOS-DISTILL-003: a deliberate, bounded extension of the "reads no bodies except compose" rule — the scanner now reads the BODIES of detected `package.json` (deps/devDeps), `requirements.txt`, `pyproject.toml` (PEP 621 + poetry dependencies), and `go.mod` (module + requires), byte-capped and tolerant (try/except → skip), and maps a small CURATED table of well-known frameworks — fastapi/flask/django/starlette/pydantic/pydantic-ai/langchain, express/react/next/vue/angular/svelte/nest, gin/echo/fiber/…, and a few more — to normalized names in a new sorted, deduped `frameworks: list[str]` scan key; conservative (only high-confidence curated matches; unknown deps ignored). `run_scan` stamps `RepositoryDNA.frameworks`, feeding the Transfer Engine's technology-match boost. Partially addresses LES-016 (manifest-body deps for python/node/go frameworks); the dotnet/jvm/cargo **ecosystem breadth** is now closed by AOS-SCAN-PRECISION-001 — JVM basenames (`pom.xml`/`build.gradle`/`build.gradle.kts` → `jvm`/maven+gradle), .NET suffix manifests (`.csproj`/`.sln` → `dotnet`), and `dotnet`/`jvm` added to `ECOSYSTEM_KINDS` (rust `Cargo.toml` was already covered). AOS-SCAN-PRECISION-001 also made `SECRET_LIKE_FILENAME` test-fixture-aware (downgrades to `info`, out of `risk_flags`, under `testdata`/`tests`/`fixtures`/… — LES-017))
- Engineering Digital Twin
- Portfolio Architecture
- repository maps
- trust boundaries
- data flow
- Engineering OS strategy
- Source-classified language weighting (AOS-ARCH-SEMANTICS-001: the scan summary derives a `primary_language` from the top **source**-classified language via `LANGUAGE_CLASS` (source/config/markup/data/docs) and ranks `primary_language_hints` source-first, so config/docs-heavy repos are no longer misreported as YAML/Markdown-primary; raw `language_mix` counts retained — LES-013)
- System Genome (Foundation Intelligence Slice 2, proposed, RFC-0019) — versioned, evidence-backed multi-dimensional classification of the whole engineered system, derived deterministically from the Evidence-Spine claims (Layer 2), not from Repository DNA directly (AD-4: DNA describes code, the Genome describes the system). Separate `current`/`intended` snapshots, coverage-calibrated confidence (LES-023), archetypes, and targeted open questions

Primary artifacts:

- docs/ARCHITECTURE_STUDIO.md
- docs/ENGINEERING_DIGITAL_TWIN.md
- docs/PORTFOLIO_ARCHITECTURE.md
- docs/ENGINEERING_OS_STRATEGY.md
- docs/rfc/RFC-0019-Foundation-Intelligence-Slice-2-System-Genome-MVP.md
- docs/REPOSITORY_SCANNER.md (compose-derived `service`/`depends_on` edges + source-classified language weighting — AOS-ARCH-SEMANTICS-001)
- agents/architecture_cartographer/CLAUDE.md
- packages/aos_core/aos_core/repository_scanner.py (compose parse → service/depends_on edges; `LANGUAGE_CLASS` → `primary_language`/`language_classes`)

