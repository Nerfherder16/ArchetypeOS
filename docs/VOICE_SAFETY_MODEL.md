# Voice Safety Model

## Purpose

Voice mode must be useful without becoming dangerous.

Spoken ideas are often incomplete, ambiguous, noisy, or made while the user is driving. ArchetypeOS should treat voice input as draft intent, not final authorization.

## Safety Rule

Voice input may create drafts, notes, tasks, research requests, and review queues. It must not directly perform destructive actions by default.

## Allowed By Default

- Create voice inbox item
- Create note draft
- Create research request
- Create decision draft
- Create architecture note
- Create reminder-style task
- Summarize project status
- Read back non-sensitive summaries

## Requires Dashboard Review

- Create or update code
- Commit changes
- Push changes
- Open pull request
- Modify infrastructure
- Change secrets
- Change authentication
- Change production configuration
- Spend money through API calls
- Send external messages
- Delete or archive project data

## Driving Mode

Driving Mode should be conservative.

Allowed:

- capture idea
- ask clarifying question
- summarize back
- save to inbox
- queue research

Disallowed:

- editing repositories
- approving PRs
- merging
- changing infrastructure
- sending external communications

## Confirmation Levels

Level 0: Capture only
Level 1: Draft creation
Level 2: Internal task creation
Level 3: Agent review request
Level 4: Code or repo change
Level 5: Infrastructure or production-impacting action

Levels 4 and 5 require explicit non-driving approval.

## Audit Logging

Every voice interaction should record:

- transcript
- intent
- confidence
- proposed action
- safety level
- approval status
- resulting artifact
