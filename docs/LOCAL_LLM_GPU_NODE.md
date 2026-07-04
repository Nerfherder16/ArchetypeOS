# Local LLM GPU Node

## Purpose

The Local LLM GPU Node lets ArchetypeOS use local hardware, such as an RTX 3090 gaming PC, for private, low-cost, and repeatable engineering tasks.

## Best Uses

- embeddings
- code indexing
- first-pass repo scans
- PR diff triage
- documentation summaries
- repeated background checks
- local/private reasoning
- graph enrichment
- nightly self-learning loop

## Candidate Runtimes

- Ollama
- vLLM
- llama.cpp
- LM Studio server
- OpenAI-compatible local endpoints

## Routing Strategy

Local models are preferred for low-risk and repetitive work.

Cloud or premium models are preferred for:

- complex architecture decisions
- security reasoning
- compliance interpretation
- final recommendations
- high-stakes report generation

## Capability Declaration

The node should register:

- hardware
- model runtimes
- available models
- context size
- embedding support
- max parallel jobs
- write capability
- health status

## Safety

The local node should not receive write access by default.

## Principle

Use expensive models where they matter. Use local models where they are sufficient.
