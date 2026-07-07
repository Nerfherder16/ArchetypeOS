import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// Promoted from scripts/web_drive/drive_digest.mjs (AOS-LEARN-001, PR #36).
// Uniquely-named entities keep serial reuse of the single shared API/db safe.
const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

test('nightly digest: run digest, verify summary counts and draft recommendation', async ({
  page,
}) => {
  const projectName = `Digest Verify ${uid()}`;
  const repoName = `No Tests Repo ${uid()}`;

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  await page.getByPlaceholder('New project name').fill(projectName);
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page.getByRole('button', { name: projectName })).toBeVisible();

  // Register + scan a repo without tests so the missing-tests draft rule fires.
  await navTo(page, 'repositories');
  await page.getByPlaceholder('Repository name').fill(repoName);
  await page.getByPlaceholder('Local path').fill('demo-repo');
  await page.getByRole('button', { name: /register repository/i }).click();
  await expect(page.getByText('demo-repo')).toBeVisible();
  await page.getByRole('button', { name: /run scan/i }).first().click();
  await expect(page.getByText('Python').first()).toBeVisible({ timeout: 20000 });

  // Nightly Digest is its own rail view.
  await navTo(page, 'digest');
  await expect(page.getByRole('heading', { name: 'Nightly Digest' })).toBeVisible();

  await page.getByRole('button', { name: /run digest/i }).click();
  await expect(page.getByText(/scan runs/).first()).toBeVisible({ timeout: 15000 });

  const body = (await page.textContent('body')) ?? '';
  // Summary counts: one repository, one scan run.
  expect(body).toMatch(/1 repositories/);
  expect(body).toMatch(/scan runs/);
  // Draft recommendation from the missing-tests rule.
  expect(body).toMatch(/Add tests to/i);
  // (AOS-UI-003: the v0.1 "Voice inbox" placeholder section was dropped when the
  // stacked page became a rail shell; the digest view no longer contains it.)

  // Reload persistence.
  await page.reload();
  await page.getByRole('button', { name: projectName }).first().click();
  await navTo(page, 'digest');
  await expect(page.getByText(/scan runs/).first()).toBeVisible({ timeout: 15000 });
});
