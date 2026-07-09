import { expect, test } from '@playwright/test';

// AOS-UX-IA-001 (deliverable 3) — the global operator status strip in the topbar.
// It summarizes two project-independent operator signals: actions awaiting
// approval (GET /authority/pending) and node health (GET /nodes). Route-mocked so
// the counts are deterministic; it must also degrade gracefully when a read fails.

const NODE = (id: string, node_status: string) => ({
  id,
  name: `node-${id}`,
  node_type: 'worker',
  endpoint: null,
  node_status,
  last_seen_at: null,
  max_sensitivity: 'public',
  write_access: false,
  capabilities: [],
  status: 'active',
  version: 1,
  created_at: '2026-07-09T00:00:00Z',
  updated_at: '2026-07-09T00:00:00Z',
});

const PENDING = (id: string) => ({
  id,
  project_id: null,
  actor: 'op',
  agent: null,
  tool: null,
  action_level: 5,
  requested_capability: 'repo_write',
  target: 'x',
  reason: 'r',
  approval_status: 'pending',
  created_at: '2026-07-09T00:00:00Z',
  updated_at: '2026-07-09T00:00:00Z',
});

test('operator status strip: shows pending-approval and node-health counts', async ({ page }) => {
  await page.route('**/authority/pending', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([PENDING('a'), PENDING('b')]) }),
  );
  await page.route('**/nodes', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([NODE('1', 'healthy'), NODE('2', 'healthy'), NODE('3', 'offline')]),
    }),
  );

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  await expect(page.getByTestId('operator-status-strip')).toBeVisible();
  await expect(page.getByTestId('status-strip-approvals')).toHaveText('2 awaiting');
  await expect(page.getByTestId('status-strip-nodes')).toHaveText('2/3 nodes');
});

test('operator status strip: degrades gracefully when a read fails', async ({ page }) => {
  await page.route('**/authority/pending', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([PENDING('a')]) }),
  );
  // Nodes endpoint errors — the nodes pill must fall back, the strip must survive.
  await page.route('**/nodes', (route) => route.fulfill({ status: 500, body: 'boom' }));

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  await expect(page.getByTestId('operator-status-strip')).toBeVisible();
  await expect(page.getByTestId('status-strip-approvals')).toHaveText('1 awaiting');
  await expect(page.getByTestId('status-strip-nodes')).toHaveText('— nodes');
});
