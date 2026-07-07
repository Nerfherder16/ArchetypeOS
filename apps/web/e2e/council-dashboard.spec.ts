import { expect, test, type Locator, type Page } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-COUNCIL-002 — worker-driven Agent Council read surface.
// Mirrors decision-loop.spec.ts: same harness, same retrying web-first polling
// pattern (LES-015: never one-shot .count()).
const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

// Poll the Agent Council section's Refresh button until a review row matching
// `question` becomes visible.  Returns the matching <li> locator.
async function refreshUntilCouncilReviewAppears(page: Page, question: string): Promise<Locator> {
  const reviewRow = page.getByTestId('council-review-row').filter({ hasText: question });
  await expect(async () => {
    await page.getByRole('button', { name: 'Refresh council' }).click();
    await expect(reviewRow).toBeVisible({ timeout: 2000 });
  }).toPass({ timeout: 45000 });
  return reviewRow;
}

test('agent council dashboard: scan → council review → expand → assert verdict and agent reasoning', async ({
  page,
}) => {
  const projectName = `Council Dashboard ${uid()}`;
  const repoName = `Dashboard Repo ${uid()}`;
  const question = `Should we adopt the scanned stack for production ${uid()}?`;

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Create project (auto-selected after creation).
  await page.getByPlaceholder('New project name').fill(projectName);
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page.getByRole('button', { name: projectName })).toBeVisible();

  // Register + scan the demo-repo fixture so agents have evidence and the
  // review clears the abstention floor (confidence > ABSTAIN_CONFIDENCE=0.35).
  await navTo(page, 'repositories');
  await page.getByPlaceholder('Repository name').fill(repoName);
  await page.getByPlaceholder('Local path').fill('demo-repo');
  await page.getByRole('button', { name: /register repository/i }).click();
  await expect(page.getByText('demo-repo')).toBeVisible();
  await page.getByRole('button', { name: /run scan/i }).first().click();
  await expect(page.getByText('Python').first()).toBeVisible({ timeout: 20000 });

  // Council & Decisions (Decision Loop + Agent Council) is its own rail view.
  await navTo(page, 'council');

  // Enqueue a council review via the existing Decision Loop form (read-only
  // Agent Council section has no enqueue form per spec).
  await expect(page.getByRole('heading', { name: 'Decision Loop' })).toBeVisible();
  await page.getByPlaceholder('Council question').fill(question);
  await page.getByRole('button', { name: 'Enqueue council review' }).click();

  // The Agent Council section must be visible below Decisions & Research.
  await expect(page.getByRole('heading', { name: 'Agent Council' })).toBeVisible();

  // Poll using the Agent Council Refresh button until the review row appears.
  // The worker produces it asynchronously — never one-shot (LES-015).
  const reviewRow = await refreshUntilCouncilReviewAppears(page, question);

  // The review row must show verdict text from the known vocabulary.
  await expect(reviewRow).toContainText(
    /Accept|Reject|Defer|Research further|Simulate first|Escalate to human|Insufficient evidence/,
  );
  // Confidence must also be present in the row.
  await expect(reviewRow).toContainText(/confidence/);

  // Expand the review to load full detail via GET /council-reviews/{id}.
  await reviewRow.getByRole('button', { name: 'Show details' }).click();
  const detailPanel = page.getByTestId('council-detail-panel');
  await expect(detailPanel).toBeVisible();

  // The Final Judge heading must render inside the detail panel.
  await expect(detailPanel.getByText('Final Judge')).toBeVisible({ timeout: 10000 });

  // At least one agent card must render (worker produces four agents for a
  // scanned project).  Use toPass to tolerate async detail fetch latency.
  const firstAgentCard = page.getByTestId('council-agent-card').first();
  await expect(async () => {
    await expect(firstAgentCard).toBeVisible({ timeout: 3000 });
  }).toPass({ timeout: 15000 });

  // Agent card must contain a known agent name from the council roster.
  await expect(firstAgentCard).toContainText(
    /research_librarian|architecture_cartographer|technology_fitness_judge|security_agent/,
  );
});
