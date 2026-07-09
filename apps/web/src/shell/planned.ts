// AOS-UX-IA-001 (deliverable 2) — planned-surface catalog. The rail shows every
// surface from the system map, including planned-but-unbuilt ones marked "soon".
// This map gives each planned surface an honest, short description of what it is
// intended to be, so clicking a "soon" chip opens an informative drawer instead
// of being a dead control. Keyed by the Surface.id from workspaces.ts. Entries
// are intent statements, not promises of a delivery date.
export type PlannedInfo = {
  summary: string;
  phase?: string;
  ticket?: string;
};

export const PLANNED_SURFACES: Record<string, PlannedInfo> = {
  // Operations
  observatory: {
    summary: 'Live system observability — a real-time view of runtime health, in-flight jobs, and node activity across the control plane.',
    phase: 'Phase 4 (operator experience)',
  },
  'claude-code-bridge': {
    summary: 'A bridge to Claude Code sessions so agent work started elsewhere is visible and steerable from the control tower.',
    phase: 'Phase 4 (operator experience)',
  },
  // Council
  'final-judge': {
    summary: 'The escalation arbiter: when council agents disagree or evidence is incomplete, the Final Judge renders the deciding verdict.',
    phase: 'Phase 3 (governance)',
  },
  'pr-guardian-gate': {
    summary: 'A surface for the PR Guardian merge gate — see why a change is blocked or cleared before it lands.',
    phase: 'Phase 3 (governance)',
  },
  'work-packages': {
    summary: 'Work-package tracking: the units of planned work, their status, and how they map to the roadmap.',
    phase: 'Phase 4',
  },
  orchestration: {
    summary: 'Multi-agent orchestration control — compose and supervise agent workflows across the node network.',
    phase: 'Phase 2 (distributed vision)',
  },
  // Architect
  'digital-twin': {
    summary: 'A correctable digital twin of a system: the architecture graph plus operator corrections that survive rescans.',
    phase: 'Phase 3 (editable model)',
    ticket: 'AOS-ARCH-STUDIO-001 (foundations shipped)',
  },
  'tech-fitness': {
    summary: 'Technology-fitness scoring — evaluate a stack against the engineering constitution and fitness-over-familiarity principle.',
    phase: 'Phase 4',
  },
  recommendations: {
    summary: 'The recommendations surface: reasoned, evidence-backed suggestions with alternatives, tradeoffs, risk, and effort.',
    phase: 'Phase 4',
  },
  // Research
  'signals-ecosystem-watch': {
    summary: 'Ecosystem-watch signals — track upstream libraries, releases, and advisories relevant to the portfolio.',
    phase: 'Phase 4 (research depth)',
  },
  'knowledge-graph': {
    summary: 'A navigable knowledge graph over lessons, decisions, and evidence — relationships, not just lists.',
    phase: 'Phase 4 (research depth)',
  },
  distillation: {
    summary: 'Distillation: compress research and council output into durable, reusable knowledge.',
    phase: 'Phase 4 (research depth)',
  },
  'docs-freshness': {
    summary: 'Docs / freshness — surface stale documentation and contract-lag the coherence probe detects.',
    phase: 'Phase 4',
  },
  marketplace: {
    summary: 'A marketplace of reusable engines, agents, and patterns discovered across the portfolio.',
    phase: 'Later',
  },
  // Executive
  'portfolio-intelligence': {
    summary: 'Portfolio intelligence — cross-project posture, maturity, and risk at a glance.',
    phase: 'Phase 4',
  },
  'evolution-scorecards': {
    summary: 'Evolution scorecards: how each system is maturing over time against its fitness goals.',
    phase: 'Phase 4',
  },
  'strategy-planner': {
    summary: 'A strategy planner for sequencing work across the portfolio with dependencies and effort.',
    phase: 'Later',
  },
  reports: {
    summary: 'Generated executive reports — summaries, evidence, and recommendations for stakeholders.',
    phase: 'Later',
  },
  // Builder
  'claude-code-session': {
    summary: 'An embedded Claude Code session for building directly inside the control tower.',
    phase: 'Phase 4',
  },
  'creation-loop': {
    summary: 'The creation loop: research → model → build → validate → evolve, tracked as one repeatable flow.',
    phase: 'Later',
  },
  'test-ci': {
    summary: 'Test results / CI — surface build and test status for the work in progress.',
    phase: 'Phase 4',
  },
  'simulation-lab': {
    summary: 'A simulation lab to try architecture changes against a model before committing them.',
    phase: 'Later',
  },
};
