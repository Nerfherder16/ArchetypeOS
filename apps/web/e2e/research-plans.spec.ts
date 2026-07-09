import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-RESEARCH-003 (UI) — the Research Plans surface. Create a plan from a
// question, run it, and inspect the run (phases, accepted/rejected sources with
// reasons + operator override, conflicts, cited findings, open questions). All
// endpoints are route-mocked so the flow is deterministic.

const PROJECT = {
  id: 'proj-rp-1', name: 'Recall', slug: 'recall', status: 'active', version: 1,
  created_at: '2026-07-09T00:00:00Z', updated_at: '2026-07-09T00:00:00Z',
};

const PLAN = {
  id: 'plan-1', project_id: PROJECT.id, question: 'best vector database', sensitivity: 'public',
  plan_status: 'planned', required_source_types: ['official-docs'],
  search_queries: ['best vector database', 'best vector database alternatives'],
  verification_steps: ['corroborate across two sources'], synthesis_policy: { cite_sources: true },
  status: 'active', version: 1, created_at: '2026-07-09T00:00:00Z', updated_at: '2026-07-09T00:00:00Z',
};

const RUN = {
  id: 'run-1', plan_id: PLAN.id, project_id: PROJECT.id, job_id: 'job-1', run_status: 'completed',
  phases: [
    { phase: 'plan', detail: '2 queries planned' },
    { phase: 'search', detail: 'over local corpus' },
    { phase: 'fetch', detail: 'gathered 2 sources' },
    { phase: 'verify', detail: '1 accepted, 1 rejected' },
    { phase: 'synthesize', detail: '1 finding' },
  ],
  sources: [
    { ref: 'vault/qdrant.md', title: 'Qdrant guide', tier: 'official-docs', score: 0.9, accepted: true, reason: null },
    { ref: 'vault/billing.md', title: 'Billing note', tier: null, score: 0, accepted: false, reason: 'does not address the question' },
  ],
  findings: [{ claim: 'Qdrant covers sharding', source_ref: 'vault/qdrant.md', tier: 'official-docs', label: 'documentation' }],
  conflicts: [], open_questions: ['benchmark qdrant vs milvus'], confidence: 0.72,
  status: 'active', version: 1, created_at: '2026-07-09T00:00:00Z', updated_at: '2026-07-09T00:00:00Z',
};

test('research plans: create a plan, run it, inspect the run, override a source', async ({ page }) => {
  let planCreated = false;
  let runProduced = false;

  await page.route('**/projects', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([PROJECT]) });
    } else {
      await route.fallback();
    }
  });
  await page.route(`**/projects/${PROJECT.id}/research-plans`, async (route) => {
    if (route.request().method() === 'POST') {
      planCreated = true;
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(PLAN) });
    } else {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(planCreated ? [PLAN] : []) });
    }
  });
  await page.route(`**/research-plans/${PLAN.id}/run`, async (route) => {
    runProduced = true;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 'job-1', job_type: 'research_run', status: 'queued', project_id: PROJECT.id, payload: { plan_id: PLAN.id } }) });
  });
  await page.route(`**/research-plans/${PLAN.id}/runs`, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(runProduced ? [RUN] : []) });
  });
  await page.route('**/research-runs/run-1/sources/**/decision', async (route) => {
    const overridden = { ...RUN, sources: [{ ...RUN.sources[0] }, { ...RUN.sources[1], accepted: true, reason: 'operator accepted' }] };
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(overridden) });
  });

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await page.getByRole('button', { name: /Recall.*active/i }).click();
  await navTo(page, 'research-plans');
  await expect(page.getByTestId('research-plans-view')).toBeVisible();

  // Create a plan.
  await page.getByTestId('research-plan-question').fill('best vector database');
  await page.getByTestId('research-plan-create').click();
  await expect(page.getByTestId('research-plan-detail-question')).toHaveText('best vector database');
  await expect(page.getByTestId('research-plan-queries')).toContainText('alternatives');

  // Run it → the run appears with its phases in order.
  await page.getByTestId('research-plan-run').click();
  await page.getByTestId('research-run-row').first().getByRole('button').click();
  await expect(page.getByTestId('research-run-detail')).toBeVisible();
  await expect(page.getByTestId('research-run-phases').getByRole('listitem')).toHaveCount(5);

  // Sources show accepted/rejected; a finding cites its source; open questions listed.
  await expect(page.getByTestId('research-run-source')).toHaveCount(2);
  await expect(page.getByTestId('research-run-finding')).toContainText('vault/qdrant.md');
  await expect(page.getByTestId('research-run-open-questions')).toContainText('benchmark qdrant');

  // Operator override: accept the rejected source → it flips to accepted.
  await page.getByTestId('research-run-source').nth(1).getByTestId('research-source-accept').click();
  await expect(page.getByTestId('research-run-source').nth(1)).toContainText('accepted');
});
