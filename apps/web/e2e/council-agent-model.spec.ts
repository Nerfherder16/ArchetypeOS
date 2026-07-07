import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-UI-010 — the per-agent model badge on the Council dashboard renders from
// `CouncilAgentOutput.agent_model` (populated by the multi-model council,
// AOS-LLM-EVAL-001 / #101). Route-stubbed so it does not need a live worker /
// real multi-model provider: the deterministic CI provider sets `model=None`,
// so the badge only appears when a real model produced the output.
const PROJECT = {
  id: 'p1',
  name: 'Model Badge Project',
  slug: 'model-badge',
  description: null,
  status: 'active',
  version: 1,
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
};
const REVIEW_ID = 'r1';
const SUMMARY = {
  id: REVIEW_ID,
  question: 'Adopt the multi-model council?',
  verdict: 'Accept with warnings',
  confidence: 0.86,
  provider: 'rotating',
  status: 'complete',
  agent_outputs: [],
};
const DETAIL = {
  ...SUMMARY,
  agreements: [],
  disagreements: [],
  unsupported_claims: [],
  follow_up: [],
  agent_outputs: [
    {
      id: 'a1', review_id: REVIEW_ID, agent_name: 'Research Librarian', agent_type: 'research',
      status: 'Complete', summary: 'ok', findings: [], evidence: [], concerns: [],
      confidence: 0.8, agent_model: 'llama-3.3-70b',
    },
    {
      id: 'a2', review_id: REVIEW_ID, agent_name: 'Security Agent', agent_type: 'security',
      status: 'Complete', summary: 'ok', findings: [], evidence: [], concerns: [],
      confidence: 0.7, agent_model: 'qwen-2.5-72b',
    },
  ],
};

const json = (body: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });

test('council dashboard: per-agent model badge renders from agent_model', async ({ page }) => {
  await page.route('**/projects', (route) =>
    route.request().method() === 'GET' ? route.fulfill(json([PROJECT])) : route.continue(),
  );
  await page.route('**/projects/*/council-reviews', (route) =>
    route.request().method() === 'GET' ? route.fulfill(json([SUMMARY])) : route.continue(),
  );
  await page.route('**/council-reviews/*', (route) => route.fulfill(json(DETAIL)));

  await page.goto('/');
  // Select the stubbed project (rail-foot selector, always present in the shell).
  await page.getByRole('button', { name: PROJECT.name }).first().click();
  await navTo(page, 'council');

  const row = page.getByTestId('council-review-row');
  await expect(row).toBeVisible({ timeout: 10000 });
  await row.getByRole('button', { name: 'Show details' }).click();

  const badges = page.getByTestId('council-agent-model');
  await expect(badges.filter({ hasText: 'llama-3.3-70b' })).toBeVisible({ timeout: 10000 });
  await expect(badges.filter({ hasText: 'qwen-2.5-72b' })).toBeVisible();
});
