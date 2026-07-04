# Arbiter And Final Judge

## Purpose

The Arbiter and Final Judge govern how ArchetypeOS resolves disagreement, uncertainty, incomplete evidence, and conflicting recommendations.

## Arbiter Role

The Arbiter defines the rules of judgment.

It answers:

- How much evidence is enough?
- When should the system abstain?
- How are conflicts resolved?
- How is confidence calculated?
- When is a recommendation rejected?

## Final Judge Role

The Final Judge applies the Arbiter rules to actual council outputs.

The Final Judge does not generate first-pass ideas. It reviews agent outputs and produces the final recommendation.

## Required Review Criteria

- Evidence quality
- Source reliability
- Agreement between agents
- Security objections
- Compliance objections
- Cost and migration impact
- Reversibility
- Acceptance criteria
- Confidence

## Possible Verdicts

- Accept
- Accept with warnings
- Reject
- Defer
- Research further
- Simulate first
- Escalate to human

## Abstention Rule

If evidence is insufficient, the correct output is not a guess. The correct output is `Insufficient evidence` with a list of what must be verified.

## Principle

The Final Judge exists to protect the system from confident but unsupported conclusions.
