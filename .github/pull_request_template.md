## Summary

Describe the change and why it is needed.

## Scope Traceability

Link the governing docs/RFCs:

- `docs/V0_1_SCOPE_LOCK.md`
- `docs/CAPABILITY_MAP.md`
- `docs/CONCRETE_BUILD_PATH.md`
- Related RFC/ADR:

## Architecture Impact

Describe affected runtime services, models, graph/data flows, or repository knowledge artifacts.

## Documentation Impact

- [ ] Documentation updated
- [ ] Capability Map updated or not affected
- [ ] Decision/RFC/ADR updated or not affected
- [ ] Knowledge vault artifacts updated or not affected

## Tests / Verification

- [ ] API tests added/updated or not affected
- [ ] Worker tests added/updated or not affected
- [ ] Web build passes or not affected
- [ ] Docker Compose config validates or not affected
- [ ] Local pre-PR guardian run completed
- [ ] Branch protection / required CI impact reviewed or not affected

Command:

```bash
scripts/pre_pr_guardian.sh
```

Post-merge command:

```bash
scripts/post_merge_validation.sh
```

## Risk Notes

Describe security, data, repository, runtime, CI, Docker, and authority/approval risks.

## PR Guardian Overrides

Only use with rationale. Delete unused lines.

<!-- PR_GUARDIAN_OVERRIDE_TESTS: rationale -->
<!-- PR_GUARDIAN_OVERRIDE_WEB_TESTS: rationale -->
<!-- PR_GUARDIAN_OVERRIDE_DOCS: rationale -->
<!-- PR_GUARDIAN_OVERRIDE_CAPABILITY_MAP: rationale -->
<!-- PR_GUARDIAN_OVERRIDE_HIGH_RISK_ACK: rationale -->

## Final Checklist

- [ ] No secrets committed
- [ ] No runtime junk committed
- [ ] No out-of-scope v0.1 capability added without RFC
- [ ] Human approval required for any destructive/high-impact action remains intact
- [ ] Required CI checks are expected to gate this PR
