import { expect, test } from '@playwright/test';

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
  await page.getByPlaceholder('Repository name').fill(repoName);
  await page.getByPlaceholder('Local path').fill('demo-repo');
  await page.getByRole('button', { name: /register repository/i }).click();
  await expect(page.getByText('demo-repo')).toBeVisible();
  await page.getByRole('button', { name: /run scan/i }).first().click();
  await expect(page.getByText('Python').first()).toBeVisible({ timeout: 20000 });

  await expect(page.getByRole('heading', { name: 'Nightly Digest' })).toBeVisible();

  await page.getByRole('button', { name: /run digest/i }).click();
  await expect(page.getByText(/scan runs/).first()).toBeVisible({ timeout: 15000 });

  const body = (await page.textContent('body')) ?? '';
  // Summary counts: one repository, one scan run.
  expect(body).toMatch(/1 repositories/);
  expect(body).toMatch(/scan runs/);
  // Draft recommendation from the missing-tests rule.
  expect(body).toMatch(/Add tests to/i);
  // The voice-inbox placeholder is retained.
  expect(body).toMatch(/Voice inbox/i);

  // Reload persistence.
  await page.reload();
  await page.getByRole('button', { name: projectName }).first().click();
  await expect(page.getByText(/scan runs/).first()).toBeVisible({ timeout: 15000 });
});
