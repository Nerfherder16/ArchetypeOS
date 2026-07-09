import { expect, test } from '@playwright/test';

// AOS-UX-IA-001 (deliverable 4) — per-workspace Now / Next / Blocked. A compact
// rail summary scoped to the current workspace mode: Now = the active surface,
// Next = the mode's first planned surface, Blocked = pending approvals (shown
// only when > 0). Now/Next derive from static workspace data; Blocked is mocked.

test('workspace status: Now shows the active surface, Next the first planned surface', async ({ page }) => {
  // No pending approvals → Blocked row stays hidden.
  await page.route('**/authority/pending', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
  );

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Default mode is Executive; its live Overview surface is active, and its first
  // planned surface is "Portfolio Intelligence".
  await expect(page.getByTestId('workspace-status')).toBeVisible();
  await expect(page.getByTestId('workspace-status-now')).toHaveText('Overview');
  await expect(page.getByTestId('workspace-status-next')).toHaveText('Portfolio Intelligence');
  await expect(page.getByTestId('workspace-status-blocked')).toHaveCount(0);
});

test('workspace status: switching mode updates Now and Next', async ({ page }) => {
  await page.route('**/authority/pending', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
  );

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  await page.getByTestId('mode-architect').click();

  // Architect routes to its first live surface (Repositories); its first planned
  // surface is "Digital Twin".
  await expect(page.getByTestId('workspace-status-now')).toHaveText('Repositories');
  await expect(page.getByTestId('workspace-status-next')).toHaveText('Digital Twin');
});

test('workspace status: Blocked appears when approvals are pending', async ({ page }) => {
  const pending = (id: string) => ({
    id, project_id: null, actor: 'op', agent: null, tool: null, action_level: 5,
    requested_capability: 'repo_write', target: 't', reason: 'r', approval_status: 'pending',
    created_at: '2026-07-09T00:00:00Z', updated_at: '2026-07-09T00:00:00Z',
  });
  await page.route('**/authority/pending', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([pending('a'), pending('b'), pending('c')]) }),
  );

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  await expect(page.getByTestId('workspace-status-blocked')).toContainText('3 awaiting approval');
});
