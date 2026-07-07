/*
 * orb.ts — pure, testable helpers for the Operations Command deck (AOS-UI-009).
 *
 * Extracted from the approved deck mock (deck_v3) so the visual engine's math is
 * unit-testable with no DOM and no React. Only pure functions + the council
 * registry live here; all canvas/render/lifecycle plumbing stays in CommandDeck.
 */

// The six Council agents (AGENT_CATALOG council). `color` mirrors the design
// tokens `--agent-librarian … --agent-security` in src/design/tokens.css exactly
// — duplicated as hex here because the additive-glow renderer builds RGB channels
// numerically and cannot resolve CSS custom properties per-dot. Keep in sync with
// tokens.css if those hues ever change.
export type AgentSpec = {
  id: string;
  label: string;
  role: string;
  /** Mirrors `--agent-<id>` in design/tokens.css. */
  color: string;
  /** Lowercase keyword triggers for deterministic routing. */
  keywords: string[];
  // Orbit parameters (radius factor, vertical tilt, phase, vertical bias, size).
  rad: number;
  tilt: number;
  ph: number;
  vy: number;
  sz: number;
};

export const AGENTS: AgentSpec[] = [
  {
    id: 'librarian',
    label: 'LIBRARIAN',
    role: 'Research',
    color: '#35d0f0',
    keywords: ['research', 'source', 'find', 'vector', 'database', 'library', 'docs', 'benchmark'],
    rad: 1.02,
    tilt: 0.42,
    ph: 0.2,
    vy: -0.1,
    sz: 0.34,
  },
  {
    id: 'cartographer',
    label: 'CARTOGRAPHER',
    role: 'Architecture',
    color: '#4f7cf7',
    keywords: ['architecture', 'map', 'arch', 'graph', 'dependency', 'spine', 'diagram', 'flow'],
    rad: 0.82,
    tilt: 0.55,
    ph: 1.1,
    vy: 0.16,
    sz: 0.3,
  },
  {
    id: 'fitness',
    label: 'FITNESS',
    role: 'Tech Fitness',
    color: '#7b5cf5',
    keywords: ['fitness', 'compare', 'workload', 'stack', 'choose', 'technology', 'tradeoff'],
    rad: 1.18,
    tilt: 0.32,
    ph: 2.3,
    vy: 0.05,
    sz: 0.26,
  },
  {
    id: 'scout',
    label: 'SCOUT',
    role: 'Repo Scout',
    color: '#b45cf0',
    keywords: ['scout', 'github', 'mcp', 'skill', 'tool', 'framework', 'discover', 'candidate'],
    rad: 1.1,
    tilt: 0.38,
    ph: 4.5,
    vy: 0.2,
    sz: 0.28,
  },
  {
    id: 'guardian',
    label: 'GUARDIAN',
    role: 'Verification',
    color: '#ff3d68',
    keywords: ['guardian', 'gate', 'verify', 'check', 'pr', 'review', 'block', 'diff', 'merge'],
    rad: 0.96,
    tilt: 0.5,
    ph: 5.5,
    vy: -0.04,
    sz: 0.32,
  },
  {
    id: 'security',
    label: 'SECURITY',
    role: 'Security',
    color: '#ff2f3f',
    keywords: ['security', 'threat', 'secret', 'auth', 'vuln', 'surface', 'supply'],
    rad: 0.9,
    tilt: 0.48,
    ph: 3.4,
    vy: -0.18,
    sz: 0.31,
  },
];

/** The core Orchestrator hue — mirrors `--signal-bright` (cyan) in tokens.css. */
export const CORE_RGB: readonly [number, number, number] = [99, 236, 251];
/** The core inner shell hue (periwinkle) — mirrors `--lex` in tokens.css. */
export const SHELL_RGB: readonly [number, number, number] = [91, 141, 240];

export type Point3 = [number, number, number];

/**
 * Fibonacci sphere: `n` points spread evenly on the unit sphere. Every returned
 * point is unit length (within ±1e-6). The n===1 edge is guarded so the y-span
 * denominator never divides by zero (a single point sits at the pole).
 */
export function fib(n: number): Point3[] {
  const out: Point3[] = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  const denom = n > 1 ? n - 1 : 1;
  for (let i = 0; i < n; i += 1) {
    const y = 1 - (i / denom) * 2;
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const t = golden * i;
    out.push([Math.cos(t) * r, y, Math.sin(t) * r]);
  }
  return out;
}

/** RGB channels for a `#rrggbb` hex string. */
export function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/**
 * Deterministic keyword routing: returns the index of the best-matching agent
 * (most keyword hits as substrings of the lowercased task). Ties resolve to the
 * earliest agent; no match falls back to agent 0 (Librarian).
 */
export function routeForTask(text: string): number {
  const q = text.toLowerCase();
  let best = 0;
  let idx = 0;
  AGENTS.forEach((agent, i) => {
    const score = agent.keywords.reduce((acc, kw) => acc + (q.includes(kw) ? 1 : 0), 0);
    if (score > best) {
      best = score;
      idx = i;
    }
  });
  return best > 0 ? idx : 0;
}
