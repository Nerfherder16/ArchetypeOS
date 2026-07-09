import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-ARCH-STUDIO-001 (UI) — the Architecture view is now an editable model
// (eval Finding 7). Covers: nodes + edges render; clicking a node opens the
// detail drawer with its evidence; typing a correction and saving PATCHes the
// backend and marks the node corrected after refresh. The repository list,
// architecture graph, DNA, and the correction PATCH are all route-mocked so the
// flow is deterministic without a real scan.

const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

const REPO = {
  id: 'repo-arch-1',
  project_id: 'ignored',
  name: 'Scan Target',
  local_path: 'scan-target',
  default_branch: 'main',
  last_scanned_at: '2026-07-08T00:00:00Z',
  status: 'active',
  version: 1,
  created_at: '2026-07-08T00:00:00Z',
  updated_at: '2026-07-08T00:00:00Z',
};

const NODE = {
  id: 'node-arch-1',
  label: 'src',
  type: 'directory',
  confidence: 0.5,
  evidence: ['read-only repository scanner'],
  risks: ['no tests found'],
  manual_correction: null as string | null,
};

const graph = (correction: string | null) => ({
  nodes: [{ ...NODE, manual_correction: correction }],
  edges: [
    {
      id: 'edge-arch-1',
      type: 'contains',
      from_node_id: 'root-1',
      to_node_id: 'node-arch-1',
      confidence: 0.9,
      evidence: ['directory tree'],
      manual_correction: null,
    },
  ],
});

test('architecture studio: node drawer edits a correction and marks it corrected', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    // The DNA endpoint is intentionally mocked 404 (unconfigured); the browser
    // logs that network 404 as a resource-load console error, which is benign.
    if (msg.type() === 'error' && !msg.text().includes('Failed to load resource')) {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => consoleErrors.push(err.message));

  let corrected: string | null = null;
  let patchBody: Record<string, unknown> | null = null;

  await page.route('**/projects/*/repositories', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([REPO]) });
    } else {
      await route.fallback();
    }
  });
  await page.route('**/repositories/*/dna', async (route) => {
    await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'no dna' }) });
  });
  await page.route('**/projects/*/architecture*', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(graph(corrected)) });
  });
  await page.route('**/architecture/nodes/node-arch-1', async (route) => {
    patchBody = JSON.parse(route.request().postData() || '{}');
    corrected = (patchBody as { manual_correction: string | null }).manual_correction;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...NODE, manual_correction: corrected }) });
  });

  const projectName = `Arch Studio ${uid()}`;
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await page.getByPlaceholder('New project name').fill(projectName);
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page.getByRole('button', { name: projectName })).toBeVisible();

  // Select the (mocked) repository, then open the Architecture view.
  await navTo(page, 'repositories');
  await page.getByRole('button', { name: 'Scan Target' }).click();
  await navTo(page, 'architecture');

  const studio = page.getByTestId('architecture-studio');
  await expect(studio).toBeVisible();
  await expect(page.getByTestId('architecture-node')).toHaveCount(1);
  await expect(page.getByTestId('architecture-edge')).toHaveCount(1);

  // Open the node detail drawer; its evidence is shown.
  await page.getByTestId('architecture-node').click();
  const drawer = page.getByTestId('architecture-drawer');
  await expect(drawer).toBeVisible();
  await expect(drawer.getByTestId('architecture-drawer-evidence')).toContainText('read-only repository scanner');
  await expect(drawer.getByTestId('architecture-drawer-risks')).toContainText('no tests found');

  // Correct the node and save → PATCH fires, drawer closes, node marked corrected.
  await page.getByTestId('architecture-correction-input').fill('actually the web frontend');
  await page.getByTestId('architecture-correction-save').click();

  await expect(page.getByTestId('architecture-drawer')).toHaveCount(0);
  await expect(page.getByTestId('architecture-node-corrected')).toBeVisible();
  expect(patchBody).toEqual({ manual_correction: 'actually the web frontend' });
  expect(consoleErrors).toEqual([]);
});

test('architecture studio: surfaces a graph error without crashing', async ({ page }) => {
  await page.route('**/projects/*/repositories', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([REPO]) });
    } else {
      await route.fallback();
    }
  });
  await page.route('**/repositories/*/dna', async (route) => {
    await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'no dna' }) });
  });
  await page.route('**/projects/*/architecture*', async (route) => {
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) });
  });

  const projectName = `Arch Studio Err ${uid()}`;
  await page.goto('/');
  await page.getByPlaceholder('New project name').fill(projectName);
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page.getByRole('button', { name: projectName })).toBeVisible();

  await navTo(page, 'repositories');
  await page.getByRole('button', { name: 'Scan Target' }).click();
  await navTo(page, 'architecture');

  await expect(page.getByTestId('architecture-error')).toBeVisible();
});
