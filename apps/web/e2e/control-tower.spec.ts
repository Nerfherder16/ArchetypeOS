import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// Promoted from scripts/web_drive/drive.mjs (AOS-CTRL-001, PR #27).
// Uniquely-named entities keep serial reuse of the single shared API/db safe.
const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

test('control tower: create project, register + scan repo, inspect DNA and architecture', async ({
  page,
}) => {
  const projectName = `Control Tower Verify ${uid()}`;
  const repoName = `Demo Repo ${uid()}`;

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Redis is absent, but /health returns 200 "degraded" (PR #39) rather than
  // 500, so the app renders normally — the Projects section is present.
  await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible();

  // Create a project via the form; the app auto-selects the created project.
  await page.getByPlaceholder('New project name').fill(projectName);
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page.getByRole('button', { name: projectName })).toBeVisible();

  // Repositories (+ Scan Summary) now live in their own rail view.
  await navTo(page, 'repositories');

  // Register a repository pointing at the committed demo-repo fixture.
  await page.getByPlaceholder('Repository name').fill(repoName);
  await page.getByPlaceholder('Local path').fill('demo-repo');
  await page.getByRole('button', { name: /register repository/i }).click();
  await expect(page.getByText('demo-repo')).toBeVisible();

  // An unscanned repository shows "never" for last-scanned.
  await expect(page.getByText('never').first()).toBeVisible();

  // Run the scan; the summary must report the detected Python source.
  await page.getByRole('button', { name: /run scan/i }).first().click();
  await expect(page.getByText('Python').first()).toBeVisible({ timeout: 20000 });

  // .env risk flag: the fixture's Dockerfile with no .env template surfaces the
  // DOCKER_WITHOUT_ENV_TEMPLATE flag ("...no .env.example/.env.sample template").
  const bodyText = (await page.textContent('body')) ?? '';
  expect(bodyText).toMatch(/\.env/i);
  // Docker detected in the scan summary ("Has Docker: yes").
  expect(bodyText).toMatch(/docker/i);

  // Architecture is its own rail view.
  await navTo(page, 'architecture');

  // Architecture view shows node and edge counts. The restyle replaced the
  // <section> wrapper with a native `.aos-view`, so read the counts from the
  // page body rather than scoping to a <section>.
  const archText = (await page.textContent('body')) ?? '';
  const nodeMatch = archText.match(/Nodes:\s*(\d+)/);
  const edgeMatch = archText.match(/Edges:\s*(\d+)/);
  expect(nodeMatch).not.toBeNull();
  expect(edgeMatch).not.toBeNull();
  expect(Number(nodeMatch![1])).toBeGreaterThanOrEqual(1);
  await expect(page.getByText(/\(repository\)/)).toBeVisible();

  // Reload: stored DNA must persist (GET /repositories/{id}/dna).
  await page.reload();
  await page.getByRole('button', { name: projectName }).first().click();
  await navTo(page, 'repositories');
  await expect(page.getByText('demo-repo')).toBeVisible();
  await page.getByRole('button', { name: repoName }).first().click();
  await expect(page.getByText('Python').first()).toBeVisible({ timeout: 20000 });
});
