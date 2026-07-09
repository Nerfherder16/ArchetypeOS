import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-WEB-SPINE-001 (slice 3b) — the Repositories surface moved into its own
// module (features/repositories/RepositoriesView.tsx). project-context.spec.ts
// covers the read paths (list + DNA); this locks the write path that lives in
// the new module: the registration form -> POST /projects/{id}/repositories ->
// list reload. Mocks keep it hermetic (no worker / real API needed).

const PROJECT = {
  id: 'proj-repo-1', name: 'Recall', slug: 'recall', status: 'active', version: 1,
  created_at: '2026-07-08T00:00:00Z', updated_at: '2026-07-08T00:00:00Z',
};

const NEW_REPO = {
  id: 'repo-new-1', project_id: PROJECT.id, name: 'recall-api', local_path: '/srv/recall-api',
  default_branch: 'main', remote_url: null, is_read_only: false, status: 'active',
  last_scanned_at: null, version: 1, created_at: '2026-07-08T00:00:00Z', updated_at: '2026-07-08T00:00:00Z',
};

test('repositories view: registering a repository posts it and reloads the list', async ({ page }) => {
  let postBody: Record<string, unknown> | null = null;
  let registered = false;

  await page.route('**/projects', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([PROJECT]) });
    } else {
      await route.fallback();
    }
  });
  await page.route(`**/projects/${PROJECT.id}/repositories`, async (route) => {
    const method = route.request().method();
    if (method === 'POST') {
      postBody = route.request().postDataJSON();
      registered = true;
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(NEW_REPO) });
    } else if (method === 'GET') {
      // Empty until the repo is registered, then it appears (list reload).
      const body = registered ? [NEW_REPO] : [];
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    } else {
      await route.fallback();
    }
  });

  await page.goto('/');
  await page.getByRole('button', { name: /Recall.*active/i }).click();
  await navTo(page, 'repositories');

  // Empty state before registering anything.
  await expect(page.getByText('No repositories registered yet.')).toBeVisible();

  // Fill and submit the registration form (handler lives in RepositoriesView).
  await page.getByPlaceholder('Repository name').fill('recall-api');
  await page.getByPlaceholder('Local path').fill('/srv/recall-api');
  await page.getByRole('button', { name: 'Register repository' }).click();

  // The POST carried the typed name + local_path, and the list reloaded.
  await expect.poll(() => postBody?.name).toBe('recall-api');
  expect(postBody?.local_path).toBe('/srv/recall-api');
  await expect(page.getByRole('button', { name: 'recall-api' })).toBeVisible();
});
