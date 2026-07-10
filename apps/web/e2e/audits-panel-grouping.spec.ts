import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-SELFHEAL-PANEL-GROUP — per-project audits section below the global board.
// Each project row shows its name and an enable/disable toggle. Enabling a project
// via PATCH /projects/{id} reveals that project's heartbeat rows. All endpoints
// are route-mocked so the flow is deterministic.

const now = new Date().toISOString();

const PROJECT = {
  id: 'proj-audit-1',
  name: 'Recall',
  slug: 'recall',
  description: null,
  status: 'active',
  audits_enabled: false,
  version: 1,
  created_at: '2026-07-09T00:00:00Z',
  updated_at: '2026-07-09T00:00:00Z',
};

const PROJECT_ENABLED = { ...PROJECT, audits_enabled: true };

function hb(overrides: Record<string, unknown>) {
  return {
    id: `hb-${String(overrides.routine ?? 'x')}`,
    routine: 'x',
    heartbeat_status: 'clean',
    day: '2026-07-09',
    pr_url: null,
    detail: null,
    project_id: null,
    status: 'active',
    version: 1,
    created_at: now,
    updated_at: now,
    ...overrides,
  };
}

// Global heartbeats (no project_id) + one per-project heartbeat.
const HEARTBEATS = [
  hb({ routine: 'conflict', heartbeat_status: 'clean' }),
  hb({ routine: 'coherence', heartbeat_status: 'findings', pr_url: 'https://github.com/Nerfherder16/ArchetypeOS/pull/42' }),
  hb({ routine: 'project-audit', heartbeat_status: 'clean', project_id: PROJECT.id, detail: 'all checks passed' }),
];

test('per-project audits: project renders; toggle issues PATCH; heartbeats appear when enabled', async ({ page }) => {
  let patchCalled = false;

  await page.route('**/audits/heartbeats', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(HEARTBEATS) });
  });

  await page.route('**/projects', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([PROJECT]) });
    } else {
      await route.fallback();
    }
  });

  await page.route(`**/projects/${PROJECT.id}`, async (route) => {
    if (route.request().method() === 'PATCH') {
      patchCalled = true;
      const body = JSON.parse(route.request().postData() ?? '{}') as { audits_enabled?: boolean };
      expect(body.audits_enabled).toBe(true);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PROJECT_ENABLED) });
    } else {
      await route.fallback();
    }
  });

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await navTo(page, 'audits');
  await expect(page.getByTestId('audits-view')).toBeVisible();

  // The per-project section renders the project row.
  const projectRow = page.getByTestId('audits-project-row').filter({ hasText: 'Recall' });
  await expect(projectRow).toBeVisible();

  // The toggle is in "Disabled" state initially (audits_enabled: false).
  const toggle = projectRow.getByTestId('audits-project-toggle');
  await expect(toggle).toHaveAttribute('aria-pressed', 'false');
  await expect(toggle).toHaveText('Disabled');

  // No project heartbeat rows before enabling.
  await expect(projectRow.getByTestId('audits-project-heartbeat')).toHaveCount(0);

  // Click the toggle — should issue PATCH and flip to enabled.
  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-pressed', 'true');
  await expect(toggle).toHaveText('Enabled');
  expect(patchCalled).toBe(true);

  // Once enabled, the project's heartbeat row appears.
  await expect(projectRow.getByTestId('audits-project-heartbeat')).toHaveCount(1);
  await expect(projectRow.getByTestId('audits-project-heartbeat')).toContainText('all checks passed');

  // The global board above is unaffected: still 4 known-routine rows.
  await expect(page.getByTestId('audit-row')).toHaveCount(4);
});
