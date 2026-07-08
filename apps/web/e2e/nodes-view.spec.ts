import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-NODE-001 (UI) — the Operations → Nodes / Runtime dashboard. Covers: the
// nav surface routes to the view; registered nodes render with health, safety
// posture (read-only vs write, sensitivity ceiling) and declared capabilities;
// and the empty state shows when no node has registered. GET /nodes is mocked so
// the fleet view is deterministic regardless of server state.

const NODES = [
  {
    id: 'node-e2e-1',
    name: 'orchestrator-laptop',
    node_type: 'orchestrator',
    endpoint: 'http://100.123.29.114:8080',
    node_status: 'healthy',
    last_seen_at: '2026-07-08T00:00:00Z',
    max_sensitivity: 'restricted',
    write_access: true,
    capabilities: [
      { id: 'cap-1', capability: 'repository_scan', capability_version: '1', capability_status: 'active', limits: {} },
      { id: 'cap-2', capability: 'council_review', capability_version: null, capability_status: 'active', limits: {} },
    ],
    status: 'active',
    version: 1,
    created_at: '2026-07-08T00:00:00Z',
    updated_at: '2026-07-08T00:00:00Z',
  },
  {
    id: 'node-e2e-2',
    name: 'research-worker',
    node_type: 'worker',
    endpoint: null,
    node_status: 'degraded',
    last_seen_at: null,
    max_sensitivity: 'public',
    write_access: false,
    capabilities: [],
    status: 'active',
    version: 1,
    created_at: '2026-07-08T00:00:00Z',
    updated_at: '2026-07-08T00:00:00Z',
  },
];

test('nodes view: renders registered nodes with health, posture and capabilities', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  await page.route('**/nodes', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(NODES) });
  });

  await page.goto('/');
  await navTo(page, 'nodes');

  const view = page.getByTestId('nodes-view');
  await expect(view).toBeVisible();
  await expect(page.getByTestId('nodes-count')).toHaveText('2 nodes');

  const cards = page.getByTestId('node-card');
  await expect(cards).toHaveCount(2);

  // First node: healthy, read-write, restricted ceiling, two capabilities.
  const orchestrator = cards.first();
  await expect(orchestrator).toContainText('orchestrator-laptop');
  await expect(orchestrator.getByTestId('node-status')).toHaveText('healthy');
  await expect(orchestrator).toContainText('read-write');
  await expect(orchestrator).toContainText('restricted');
  const caps = orchestrator.getByTestId('node-capabilities');
  await expect(caps).toContainText('repository_scan');
  await expect(caps).toContainText('council_review');

  // Second node: degraded, read-only, no declared capabilities.
  const worker = cards.nth(1);
  await expect(worker).toContainText('research-worker');
  await expect(worker.getByTestId('node-status')).toHaveText('degraded');
  await expect(worker).toContainText('read-only');
  await expect(worker).toContainText('No declared capabilities');

  expect(consoleErrors).toEqual([]);
});

test('nodes view: shows the empty state when no node has registered', async ({ page }) => {
  await page.route('**/nodes', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });

  await page.goto('/');
  await navTo(page, 'nodes');
  await expect(page.getByTestId('nodes-empty')).toBeVisible();
});

test('nodes view: surfaces a registry error without crashing', async ({ page }) => {
  await page.route('**/nodes', async (route) => {
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) });
  });

  await page.goto('/');
  await navTo(page, 'nodes');
  await expect(page.getByTestId('nodes-error')).toBeVisible();
});
