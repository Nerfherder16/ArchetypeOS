import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-SELFHEAL observability (UI) — the Nightly Audits board. Every known
// self-learn routine gets a row from GET /audits/heartbeats: clean, findings
// (with a PR link), missed (a heartbeat older than a day), or "no report" (a
// routine that has never checked in). The endpoint is route-mocked so the
// four resolved states are deterministic.

const now = new Date().toISOString();
const stale = new Date('2020-01-01T00:00:00Z').toISOString();

function hb(overrides: Record<string, unknown>) {
  return {
    id: `hb-${overrides.routine}`,
    routine: 'x',
    heartbeat_status: 'clean',
    day: '2026-07-09',
    pr_url: null,
    detail: null,
    status: 'active',
    version: 1,
    created_at: now,
    updated_at: now,
    ...overrides,
  };
}

// coherence reported findings today (a PR to review); conflict is clean and
// fresh; session-pain last reported clean but long ago (missed); toil is absent
// entirely (never reported).
const HEARTBEATS = [
  hb({ routine: 'coherence', heartbeat_status: 'findings', pr_url: 'https://github.com/Nerfherder16/ArchetypeOS/pull/999', detail: '3 contract-lag fields' }),
  hb({ routine: 'conflict', heartbeat_status: 'clean' }),
  hb({ routine: 'session-pain', heartbeat_status: 'clean', updated_at: stale, day: '2020-01-01' }),
];

test('nightly audits: routines resolve to clean / findings / missed / no-report', async ({ page }) => {
  await page.route('**/audits/heartbeats', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(HEARTBEATS) });
  });

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await navTo(page, 'audits');
  await expect(page.getByTestId('audits-view')).toBeVisible();

  // Four known routines, each with a row.
  await expect(page.getByTestId('audit-row')).toHaveCount(4);

  // coherence: findings, with a PR link.
  await expect(page.locator('[data-routine="coherence"]')).toHaveAttribute('data-state', 'findings');
  await expect(page.locator('[data-routine="coherence"]').getByTestId('audit-pr-link')).toHaveAttribute('href', /pull\/999/);

  // conflict: clean and fresh.
  await expect(page.locator('[data-routine="conflict"]')).toHaveAttribute('data-state', 'clean');

  // session-pain: reported, but the heartbeat is stale → missed.
  await expect(page.locator('[data-routine="session-pain"]')).toHaveAttribute('data-state', 'missed');

  // toil: never checked in.
  await expect(page.locator('[data-routine="toil"]')).toHaveAttribute('data-state', 'never');

  // The summary flags the one routine that needs attention (session-pain missed).
  await expect(page.getByTestId('audits-summary')).toContainText('1 routine needs attention');
});
