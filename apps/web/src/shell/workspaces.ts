import type { ViewId } from './Shell';

// AOS-UI-007 — workspace modes: a top-level organizing level in the rail. The 8
// shipped views group under 6 modes (per docs/WORKSPACE_LAYOUT_ENGINE.md).
// Planned-but-unbuilt surfaces appear as disabled "soon" entries so the full
// system structure from the surface map stays visible and honest. This module is
// pure data + helpers (no React), so it can be imported by both the shell and
// the e2e nav support without dragging runtime deps.
export type WorkspaceModeId =
  | 'operations'
  | 'council'
  | 'architect'
  | 'research'
  | 'executive'
  | 'builder';

export type Surface = {
  id: string; // stable slug, e.g. 'research-inbox'
  label: string;
  status: 'live' | 'soon';
  view?: ViewId; // present iff status === 'live'
  note?: string; // one-line mono subtitle (optional)
};

export type WorkspaceMode = {
  id: WorkspaceModeId;
  label: string; // e.g. 'Operations'
  focus: string; // one-line description
  surfaces: Surface[];
};

// Live surfaces reuse the existing 8 ViewIds; everything else is `soon`.
export const WORKSPACE_MODES: WorkspaceMode[] = [
  {
    id: 'operations',
    label: 'Operations',
    focus: 'Command home — live ops.',
    surfaces: [
      { id: 'command', label: 'Command', status: 'live', view: 'command' },
      { id: 'voice-inbox', label: 'Voice Inbox', status: 'live', view: 'voice-inbox' },
      { id: 'observatory', label: 'Observatory', status: 'soon' },
      { id: 'live-activity', label: 'Live Activity', status: 'live', view: 'activity' },
      { id: 'digest', label: 'Digest', status: 'live', view: 'digest' },
      { id: 'scheduling', label: 'Scheduling', status: 'live', view: 'scheduling' },
      { id: 'nodes-runtime', label: 'Nodes / Runtime', status: 'live', view: 'nodes' },
      { id: 'providers-routing', label: 'Providers & Model Routing', status: 'live', view: 'providers' },
      { id: 'claude-code-bridge', label: 'Claude Code Bridge', status: 'soon' },
    ],
  },
  {
    id: 'council',
    label: 'Council',
    focus: 'Deliberation & governance.',
    surfaces: [
      { id: 'council', label: 'Council & Decisions', status: 'live', view: 'council' },
      { id: 'final-judge', label: 'Final Judge', status: 'soon' },
      { id: 'pr-guardian-gate', label: 'PR Guardian Gate', status: 'soon' },
      { id: 'approvals-authority', label: 'Awaiting You', status: 'live', view: 'approvals' },
      { id: 'work-packages', label: 'Work Packages', status: 'soon' },
      { id: 'orchestration', label: 'Orchestration', status: 'soon' },
    ],
  },
  {
    id: 'architect',
    label: 'Architect',
    focus: 'System structure & choices.',
    surfaces: [
      { id: 'repositories', label: 'Repositories', status: 'live', view: 'repositories' },
      { id: 'architecture', label: 'Architecture', status: 'live', view: 'architecture' },
      { id: 'reuse', label: 'Reuse', status: 'live', view: 'reuse' },
      { id: 'digital-twin', label: 'Digital Twin', status: 'soon' },
      { id: 'tech-fitness', label: 'Tech Fitness', status: 'soon' },
      { id: 'recommendations', label: 'Recommendations', status: 'soon' },
    ],
  },
  {
    id: 'research',
    label: 'Research',
    focus: 'Evidence & knowledge.',
    surfaces: [
      { id: 'knowledge', label: 'Knowledge', status: 'live', view: 'knowledge' },
      { id: 'research-inbox', label: 'Research Inbox', status: 'live', view: 'research' },
      { id: 'signals-ecosystem-watch', label: 'Signals / Ecosystem Watch', status: 'soon' },
      { id: 'knowledge-graph', label: 'Knowledge Graph', status: 'soon' },
      { id: 'distillation', label: 'Distillation', status: 'soon' },
      { id: 'docs-freshness', label: 'Docs / Freshness', status: 'soon' },
      { id: 'marketplace', label: 'Marketplace', status: 'soon' },
    ],
  },
  {
    id: 'executive',
    label: 'Executive',
    focus: 'Portfolio & strategy.',
    surfaces: [
      { id: 'overview', label: 'Overview', status: 'live', view: 'overview' },
      { id: 'portfolio-intelligence', label: 'Portfolio Intelligence', status: 'soon' },
      { id: 'evolution-scorecards', label: 'Evolution Scorecards', status: 'soon' },
      { id: 'strategy-planner', label: 'Strategy Planner', status: 'soon' },
      { id: 'reports', label: 'Reports', status: 'soon' },
    ],
  },
  {
    id: 'builder',
    label: 'Builder',
    focus: 'Execution.',
    surfaces: [
      { id: 'claude-code-session', label: 'Claude Code Session', status: 'soon' },
      { id: 'creation-loop', label: 'Creation Loop', status: 'soon' },
      { id: 'test-ci', label: 'Test results / CI', status: 'soon' },
      { id: 'simulation-lab', label: 'Simulation Lab', status: 'soon' },
    ],
  },
];

// The mode whose surfaces contain a live surface with this view. All 8 shipped
// views are covered; the fallback keeps the signature total for TS.
export function modeForView(view: ViewId): WorkspaceModeId {
  for (const mode of WORKSPACE_MODES) {
    if (mode.surfaces.some((surface) => surface.status === 'live' && surface.view === view)) {
      return mode.id;
    }
  }
  return 'executive';
}

// The first live surface's view for a mode, or undefined when the mode has no
// live surface yet (builder).
export function firstLiveView(mode: WorkspaceModeId): ViewId | undefined {
  const entry = WORKSPACE_MODES.find((candidate) => candidate.id === mode);
  return entry?.surfaces.find((surface) => surface.status === 'live')?.view;
}
