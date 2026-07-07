import { expect, test, type Locator, type Page } from '@playwright/test';

// AOS-COUNCIL-PHASEC2B — worker-driven Council → draft → approve/reject → ADR loop.
// Uniquely-named entities keep serial reuse of the single shared API/db safe.
const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

// The review is produced ASYNCHRONOUSLY by the worker draining the queue, so we
// must poll with a RETRYING web-first assertion — never one-shot `count()`
// (LES-015). Click Refresh reviews until the review's Draft-decision button
// appears, then return that button.
async function refreshUntilReviewAppears(page: Page): Promise<Locator> {
  const draftButton = page.getByRole('button', { name: 'Draft decision' });
  await expect(async () => {
    await page.getByRole('button', { name: 'Refresh reviews' }).click();
    await expect(draftButton).toBeVisible({ timeout: 2000 });
  }).toPass({ timeout: 45000 });
  return draftButton;
}

// Target the drafted decision's row by its stable testid. The "Decisions &
// Research" section renders BOTH the Decision-Loop council-reviews list (each row
// echoes the question) AND the decisions list, so a section-scoped
// listitem+question locator is ambiguous — it matched the review <li> and the
// decision <li> (LES-028 fixed the cross-section case; LES-030 fixes this
// intra-section one). `data-testid="decision-row"` marks only the decision rows.
const decisionRow = (page: Page, question: string): Locator =>
  page.getByTestId('decision-row').filter({ hasText: question });

test('decision loop: scan → council review → draft → approve → export ADR', async ({ page }) => {
  const projectName = `Council Happy ${uid()}`;
  const repoName = `Council Repo ${uid()}`;
  const question = `Should we adopt the scanned stack ${uid()}?`;
  const approver = `Approver ${uid()}`;

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Create the project (auto-selected).
  await page.getByPlaceholder('New project name').fill(projectName);
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page.getByRole('button', { name: projectName })).toBeVisible();

  // Register + scan the demo-repo fixture so the review clears the abstention
  // floor (arch/fitness/security selectors get evidence → verdict + confidence).
  await page.getByPlaceholder('Repository name').fill(repoName);
  await page.getByPlaceholder('Local path').fill('demo-repo');
  await page.getByRole('button', { name: /register repository/i }).click();
  await expect(page.getByText('demo-repo')).toBeVisible();
  await page.getByRole('button', { name: /run scan/i }).first().click();
  await expect(page.getByText('Python').first()).toBeVisible({ timeout: 20000 });

  // Enqueue a council review; the worker produces it asynchronously.
  await expect(page.getByRole('heading', { name: 'Decision Loop' })).toBeVisible();
  await page.getByPlaceholder('Council question').fill(question);
  await page.getByRole('button', { name: 'Enqueue council review' }).click();

  const draftButton = await refreshUntilReviewAppears(page);

  // Draft a decision from the review → an approvable `draft`.
  await draftButton.click();
  const row = decisionRow(page, question);
  await expect(row).toBeVisible();
  await expect(row.getByText('draft', { exact: true })).toBeVisible();

  // Approve as a named human.
  await row.getByPlaceholder('Approver name').fill(approver);
  await row.getByRole('button', { name: 'Approve' }).click();
  await expect(row.getByText('approved', { exact: true })).toBeVisible();
  await expect(row.getByText(new RegExp(`approved by ${approver}`))).toBeVisible();

  // Export the approved decision to an ADR in the writable e2e vault.
  await row.getByRole('button', { name: 'Export ADR' }).click();
  await expect(row.getByText(/ADR exported to wiki\/decisions\//)).toBeVisible({ timeout: 15000 });
});

test('decision loop: no scan → abstained review → needs_evidence draft → approve 409', async ({
  page,
}) => {
  const projectName = `Council Blocked ${uid()}`;
  const question = `Should we ship without evidence ${uid()}?`;
  const approver = `Approver ${uid()}`;

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Create the project but register NO repository / run NO scan → the council
  // abstains (Insufficient evidence, confidence 0.0) → a needs_evidence draft.
  await page.getByPlaceholder('New project name').fill(projectName);
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page.getByRole('button', { name: projectName })).toBeVisible();

  await expect(page.getByRole('heading', { name: 'Decision Loop' })).toBeVisible();
  await page.getByPlaceholder('Council question').fill(question);
  await page.getByRole('button', { name: 'Enqueue council review' }).click();

  const draftButton = await refreshUntilReviewAppears(page);

  await draftButton.click();
  const row = decisionRow(page, question);
  await expect(row).toBeVisible();
  await expect(row.getByText('needs_evidence', { exact: true })).toBeVisible();

  // Attempting to approve an abstention-blocked draft surfaces the 409 inline.
  await row.getByPlaceholder('Approver name').fill(approver);
  await row.getByRole('button', { name: 'Approve' }).click();
  await expect(row.getByRole('alert')).toContainText(/cannot be approved/i);
  await expect(row.getByRole('alert')).toContainText(/evidence/i);
  // The decision stays needs_evidence (approval did not mutate state).
  await expect(row.getByText('needs_evidence', { exact: true })).toBeVisible();
});
