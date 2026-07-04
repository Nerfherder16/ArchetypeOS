# Voice Command Center

## Purpose

Voice Command Center makes ArchetypeOS usable when the developer is away from the keyboard.

It is designed for idea capture, research requests, project triage, decision drafting, and safe conversational interaction while driving, walking, or working hands-free.

## Primary Use Case

```text
Driving idea
→ voice capture
→ speech to text
→ intent classification
→ project inbox
→ agent routing
→ draft decision, research task, note, or issue
→ text to speech response
→ later review in dashboard
```

## Core Principle

Voice mode captures and prepares work. It does not directly perform destructive actions.

## Capabilities

- Capture ideas by voice
- Attach ideas to projects
- Create research tasks
- Create decision drafts
- Create architecture notes
- Create PR Guardian review requests
- Summarize project status
- Read back open decisions
- Read back recent research
- Queue work for later approval

## Voice Inbox

Every voice session should produce a Voice Inbox item.

Fields:

- transcript
- summary
- detected project
- detected intent
- suggested action
- confidence
- required review
- created date
- source device

## Intent Types

- idea_capture
- research_request
- architecture_note
- decision_draft
- todo
- risk_note
- repo_review_request
- pr_guardian_request
- design_note
- experiment_request

## Agent Routing

Voice items may route to:

- Research Librarian
- Architecture Cartographer
- Technology Fitness Judge
- Design Intelligence Agent
- PR Guardian
- Final Judge

## Review First

Voice-generated actions should remain drafts until reviewed in the dashboard, especially when they affect code, infrastructure, security, compliance, cost, or repository state.
