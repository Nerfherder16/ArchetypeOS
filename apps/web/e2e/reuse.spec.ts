import { expect, test } from '@playwright/test';

// AOS-UI-001 — Reuse view wired to the live transfer endpoint
// (POST /projects/{id}/transfer). Real API on sqlite (lexical path).
//
// The scan resolves to a well-formed TERMINAL state — either at least one
// result row (portfolio has scorable distilled repos) or the empty state —
// never a hang or an error. Uses retrying web-first assertions (LES-015: never
// a one-shot `.count()`). Harness conventions mirror council-dashboard.spec.ts.
const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

test('reuse view: create project → scan portfolio → terminal state (results or empty)', async ({
  page,
}) => {
  const projectName = `Reuse Scan ${uid()}`;
  const need = 'an LLM provider abstraction to route prompts across model backends';

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Create the project (auto-selected on create).
  await page.getByPlaceholder('New project name').fill(projectName);
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page.getByRole('button', { name: projectName })).toBeVisible();

  // The Reuse section renders once a project is selected.
  const reuseView = page.getByTestId('reuse-view');
  await expect(reuseView).toBeVisible();
  await expect(reuseView.getByText('Knowledge Transfer Engine')).toBeVisible();

  // Describe a need and run the live scan.
  await page.getByTestId('reuse-need-input').fill(need);
  await page.getByTestId('reuse-run').click();

  // Resolve to a terminal state: EITHER a result row OR the empty state — never
  // a hang. `.or()` yields the first that matches; the assertion retries.
  const firstResult = page.getByTestId('reuse-result-row').first();
  const emptyState = page.getByTestId('reuse-empty');
  await expect(firstResult.or(emptyState)).toBeVisible({ timeout: 15000 });

  // Never a request error.
  await expect(page.getByTestId('reuse-error')).toHaveCount(0);

  // If a candidate came back, expand it and assert Reason + provenance render.
  if (await firstResult.isVisible()) {
    await firstResult.getByTestId('reuse-expand').click();
    await expect(firstResult.getByText('Reason')).toBeVisible();
    await expect(firstResult.getByText(/provenance:/)).toBeVisible();
  }
});
