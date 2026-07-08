# `state-hygiene` — reusable canonical-state drift prevention

Gives any ArchetypeOS-managed repo the same doc-drift assurance the platform repo
has (AOS-STATE-RECON-001 / LES-L09): the machine-owned fields in a `CURRENT_STATE`
doc are **auto-derived from git on every merge**, so a human never maintains them
and they cannot drift. Logic lives here once; consumers carry only a tiny stub.

## What it does

On push to the default branch it rewrites, inside a delimited canonical block:

```markdown
<!-- AOS-CANONICAL:START -->
- Watermark PR: #<max merged PR, derived from git>
- Active Branch: <none (on main) | `feature/x`>
- Current Objective: <human-authored — never touched>
<!-- AOS-CANONICAL:END -->
```

It commits the change with `[skip ci]` (no workflow loop) and never edits the
human fields. Detection of residual staleness is a separate concern (the platform
repo's `tools/doc_staleness.py` nightly); this action is the *prevention* half.

## Adopt it in a repo (2 steps)

1. Add a canonical block to your state doc (default `docs/CURRENT_STATE.md`):

   ```markdown
   <!-- AOS-CANONICAL:START -->
   - Watermark PR: #0
   - Active Branch: none (on main)
   - Current Objective: <one line>
   <!-- AOS-CANONICAL:END -->
   ```

2. Add `.github/workflows/state-hygiene.yml`:

   ```yaml
   name: State hygiene
   on:
     push:
       branches: [main]
   permissions:
     contents: write
   jobs:
     refresh:
       runs-on: ubuntu-latest
       if: ${{ !contains(github.event.head_commit.message, 'chore(state)') }}
       steps:
         - uses: actions/checkout@v4
           with:
             fetch-depth: 0
         - uses: Nerfherder16/ArchetypeOS/.github/actions/state-hygiene@main
           # with:
           #   doc: docs/CURRENT_STATE.md
           #   marker: AOS-CANONICAL
   ```

The ArchetypeOS repo itself consumes this action (dogfood) via
`.github/workflows/state-canonical-refresh.yml` using the local `./` ref.

## Inputs

| Input | Default | Notes |
| --- | --- | --- |
| `doc` | `docs/CURRENT_STATE.md` | Canonical state doc path. |
| `marker` | `AOS-CANONICAL` | Block delimiters are `<!-- MARKER:START/END -->`. |
| `commit-name` / `commit-email` | `aos-state[bot]` | Author of the refresh commit. |
