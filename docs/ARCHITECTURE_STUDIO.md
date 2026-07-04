# Architecture Studio

## Purpose

Architecture Studio is the visual modeling environment for ArchetypeOS.

It creates editable architecture models from repositories, text descriptions, diagrams, Mermaid, Draw.io, Excalidraw, uploaded images, and manual input.

## Core Views

- Architecture Spine Graph
- Dependency Graph
- Data Flow
- Trust Boundaries
- Deployment Topology
- Runtime Topology
- Risk Overlay
- Recommendation Overlay

## Input Sources

- repository scan
- text description
- image upload
- Mermaid
- Draw.io
- Excalidraw
- manual graph editing

## Graph Data

Architecture must be stored as editable data, not only as images.

Minimum node fields:

- id
- label
- type
- parent
- confidence
- evidence
- risks
- related decisions

Minimum edge fields:

- from
- to
- type
- confidence
- evidence

## Analysis

Architecture Studio should detect:

- unclear boundaries
- direct data access risks
- auth bypasses
- duplicated services
- missing queues
- missing audit logs
- fragile dependencies
- documentation drift

## Principle

Architecture is not an afterthought. It is the map the rest of the system reasons against.
