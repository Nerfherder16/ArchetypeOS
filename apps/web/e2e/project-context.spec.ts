import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-WEB-SPINE-001 (slice 2) — characterizes the extracted ProjectProvider's
// core contract: selecting a project drives `loadRepositories(projectId)` and
// the Repositories view renders that project's repos. This is the wiring that
// moved out of App into shell/ProjectContext.tsx; the test locks it so later
// per-view slices can't silently break project selection. Mocks keep it
// hermetic (no worker / real API needed).

const PROJECT = {
  id: 'proj-ctx-1', name: 'Recall', slug: 'recall', status: 'active', version: 1,
  created_at: '2026-07-08T00:00:00Z', updated_at: '2026-07-08T00:00:00Z',
};

const REPO = {
  id: 'repo-ctx-1', project_id: PROJECT.id, name: 'recall-core', local_path: '/srv/recall-core',
  default_branch: 'main', remote_url: null, is_read_only: false, status: 'active',
  last_scanned_at: null, version: 1, created_at: '2026-07-08T00:00:00Z', updated_at: '2026-07-08T00:00:00Z',
};

const DNA = {
  repository_id: REPO.id, purpose: 'Local-first memory system', maturity: 'growing',
  language_mix: { Python: 0.9 }, package_managers: ['pip'], frameworks: ['FastAPI'],
  runtime_services: ['Qdrant'], deployment_files: ['docker-compose.yml'], risk_flags: [],
  evidence: [], scan_summary: { summary: { primary_language_hints: ['Python'], has_docker: true } },
  confidence: 0.8, status: 'active', version: 1,
  created_at: '2026-07-08T00:00:00Z', updated_at: '2026-07-08T00:00:00Z',
};

test('project context: selecting a project loads and renders its repositories', async ({ page }) => {
  const repoRequests: string[] = [];

  await page.route('**/projects', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([PROJECT]) });
    } else {
      await route.fallback();
    }
  });
  // The provider's loadRepositories hits GET /projects/{id}/repositories.
  await page.route(`**/projects/${PROJECT.id}/repositories`, async (route) => {
    if (route.request().method() === 'GET') {
      repoRequests.push(route.request().url());
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([REPO]) });
    } else {
      await route.fallback();
    }
  });

  await page.goto('/');

  // Before selecting a project, its repositories have not been fetched.
  expect(repoRequests).toHaveLength(0);

  // Select the project from the rail (owned by ProjectProvider now).
  await page.getByRole('button', { name: /Recall.*active/i }).click();

  // The Repositories surface shows the selected project's repos, proving the
  // selection -> loadRepositories(projectId) wiring survives the extraction.
  await navTo(page, 'repositories');
  await expect(page.getByRole('button', { name: 'recall-core' })).toBeVisible();
  await expect(page.getByRole('cell', { name: '/srv/recall-core' })).toBeVisible();

  // And the fetch was scoped to the selected project id.
  await expect.poll(() => repoRequests.length).toBeGreaterThan(0);
  expect(repoRequests.every((url) => url.includes(`/projects/${PROJECT.id}/repositories`))).toBe(true);
});

// AOS-WEB-SPINE-001 (slice 3a) — locks the RepositoryDataProvider contract:
// selecting a repository co-loads its DNA (and architecture) via the provider's
// effect, and the Repositories view's scan-summary panel renders that DNA. The
// data lifecycle moved out of App into shell/RepositoryDataContext.tsx.
test('repository data: selecting a repository loads and renders its DNA', async ({ page }) => {
  const dnaRequests: string[] = [];

  await page.route('**/projects', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([PROJECT]) });
    } else {
      await route.fallback();
    }
  });
  await page.route(`**/projects/${PROJECT.id}/repositories`, async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([REPO]) });
    } else {
      await route.fallback();
    }
  });
  // The provider's co-load effect fetches DNA + architecture for the selected repo.
  await page.route(`**/repositories/${REPO.id}/dna`, async (route) => {
    dnaRequests.push(route.request().url());
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(DNA) });
  });
  await page.route(`**/projects/${PROJECT.id}/architecture**`, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ nodes: [], edges: [] }) });
  });

  await page.goto('/');
  await page.getByRole('button', { name: /Recall.*active/i }).click();
  await navTo(page, 'repositories');

  // Select the repository -> ProjectContext.selectedRepositoryId changes ->
  // RepositoryDataProvider co-loads DNA -> the scan-summary panel renders it.
  await page.getByRole('button', { name: 'recall-core' }).click();
  await expect(page.getByText('Scan summary')).toBeVisible();
  await expect(page.getByTestId('dna-frameworks')).toHaveText('FastAPI');
  await expect.poll(() => dnaRequests.length).toBeGreaterThan(0);
  expect(dnaRequests.every((url) => url.includes(`/repositories/${REPO.id}/dna`))).toBe(true);
});
