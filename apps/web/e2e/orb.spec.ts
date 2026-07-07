import { expect, test } from '@playwright/test';
import { AGENTS, fib, hexToRgb, routeForTask } from '../src/features/command/orb';

// AOS-UI-009 — unit assertions for the PURE orb engine helpers.
//
// Same rationale as radarLayout.spec.ts: apps/web has no browser-free unit
// runner, so these pure-TS assertions ride in a Playwright spec that imports the
// module directly (Playwright transpiles TS and runs in node — no DOM needed).

test('fib: returns n points, each of unit length (±1e-6)', () => {
  for (const n of [1, 2, 7, 340, 420, 1300]) {
    const pts = fib(n);
    expect(pts).toHaveLength(n);
    for (const [x, y, z] of pts) {
      const len = Math.sqrt(x * x + y * y + z * z);
      expect(len).toBeCloseTo(1, 6);
    }
  }
});

test('fib: n = 0 is empty and n = 1 stays finite (no divide-by-zero)', () => {
  expect(fib(0)).toHaveLength(0);
  const one = fib(1);
  expect(one).toHaveLength(1);
  for (const c of one[0]) {
    expect(Number.isFinite(c)).toBe(true);
  }
});

test('routeForTask: sample tasks map to the expected council agent', () => {
  const idOf = (task: string) => AGENTS[routeForTask(task)].id;

  expect(idOf('research the best vector database for our retrieval')).toBe('librarian');
  expect(idOf('map the architecture of the pydantic-ai repo')).toBe('cartographer');
  expect(idOf('compare the technology stack tradeoffs')).toBe('fitness');
  expect(idOf('scout github for mcp servers we could reuse')).toBe('scout');
  expect(idOf('run the guardian gate on pr 92')).toBe('guardian');
  expect(idOf('threat model the exposed api surface')).toBe('security');
});

test('routeForTask: deterministic; no keyword match falls back to agent 0', () => {
  // Deterministic — identical input, identical index.
  expect(routeForTask('run the guardian gate')).toBe(routeForTask('run the guardian gate'));
  // Nothing matches → index 0 (Librarian).
  expect(routeForTask('zzz qqq nothing here')).toBe(0);
  expect(routeForTask('')).toBe(0);
});

test('AGENTS: exactly the six council agents with valid mirrored hex colors', () => {
  expect(AGENTS.map((a) => a.id)).toEqual([
    'librarian',
    'cartographer',
    'fitness',
    'scout',
    'guardian',
    'security',
  ]);
  for (const a of AGENTS) {
    expect(a.color).toMatch(/^#[0-9a-f]{6}$/i);
    const [r, g, b] = hexToRgb(a.color);
    for (const ch of [r, g, b]) {
      expect(ch).toBeGreaterThanOrEqual(0);
      expect(ch).toBeLessThanOrEqual(255);
    }
  }
});
