import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-AUTHORITY-001 (UI) — the pending authority actions queue on the Awaiting
// You surface (eval Finding 10). Covers: high-impact actions awaiting a human
// decision render with capability/target/level; and the queue degrades to an
// empty state without crashing. GET /authority/pending is route-mocked so the
// queue is deterministic; the decisions half of the view resolves to its own
// empty state against the fresh e2e API.

const PENDING = [
  {
    id: 'appr-1',
    project_id: null,
    actor: 'worker',
    agent: null,
    tool: 'git',
    action_level: 5,
    requested_capability: 'git_commit',
    target: 'main',
    reason: 'commit the generated migration',
    approval_status: 'pending',
    created_at: '2026-07-08T00:00:00Z',
    updated_at: '2026-07-08T00:00:00Z',
  },
];

test('authority queue: pending high-impact actions render with capability and level', async ({ page }) => {
  await page.route('**/authority/pending', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PENDING) });
  });

  await page.goto('/');
  await navTo(page, 'approvals');

  const queue = page.getByTestId('authority-queue');
  await expect(queue).toBeVisible();
  await expect(page.getByTestId('authority-count')).toHaveText('1 pending');

  const card = page.getByTestId('authority-action-card');
  await expect(card).toHaveCount(1);
  await expect(card).toContainText('git_commit');
  await expect(card.getByTestId('authority-action-level')).toHaveText('level 5');
  await expect(card).toContainText('target main');
});

test('authority queue: shows the empty state when nothing awaits approval', async ({ page }) => {
  await page.route('**/authority/pending', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });

  await page.goto('/');
  await navTo(page, 'approvals');
  await expect(page.getByTestId('authority-empty')).toBeVisible();
});

test('authority queue: surfaces an error without crashing', async ({ page }) => {
  await page.route('**/authority/pending', async (route) => {
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) });
  });

  await page.goto('/');
  await navTo(page, 'approvals');
  await expect(page.getByTestId('authority-error')).toBeVisible();
});
