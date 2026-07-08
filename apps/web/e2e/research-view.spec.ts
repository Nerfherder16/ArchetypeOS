import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-RES-001 — the Research "Research Inbox" surface is now a LIVE inbox that
// aggregates the platform's research notes across all projects into one
// confidence-ranked list. Frontend only — it composes the existing GET /projects
// + per-project GET /projects/{id}/research-notes endpoints. The first test uses
// the real API booted by the harness against a fresh, empty sqlite DB (no seeded
// projects), so the aggregated inbox resolves to its graceful EMPTY state —
// never a hang, throw, or white screen. The second route-stubs projects + notes
// to assert cards render ranked by confidence with a freshness pill and summary.
// Harness conventions mirror activity-view.spec.ts.

test('research view: Research surface is live and mounts the inbox gracefully', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    // Ignore the dev server's favicon.ico 404 — a static-asset quirk of the
    // Vite preview origin, not an app or API error.
    if (msg.type() === 'error' && !msg.location().url.endsWith('/favicon.ico')) {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => consoleErrors.push(err.message));

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Research mode reveals its surfaces. "Research Inbox" is now a live nav item
  // (nav-research), not a disabled `soon-*` stub. The stable surface id is kept,
  // so the old soon-* testid is gone.
  await page.getByTestId('mode-research').click();
  const researchNav = page.getByTestId('nav-research');
  await expect(researchNav).toBeVisible();
  await expect(researchNav).toHaveText(/Research Inbox/);
  await expect(page.getByTestId('soon-research-inbox')).toHaveCount(0);

  // Route to it via the shared nav helper (selects the owning mode, clicks nav).
  await navTo(page, 'research');

  // The view mounts with its heading even when no data is seeded.
  const view = page.getByTestId('research-view');
  await expect(view).toBeVisible();
  await expect(view.getByRole('heading', { name: 'Research inbox' })).toBeVisible();

  // Resolves to a terminal graceful surface: EITHER seeded cards, the empty
  // state (fresh DB), OR a readable error notice (API down) — never a hang.
  // `.or()` yields the first that matches; the assertion retries (LES-015: never
  // a one-shot `.count()`).
  const card = page.getByTestId('research-note-card').first();
  const empty = page.getByTestId('research-empty');
  const error = page.getByTestId('research-error');
  await expect(card.or(empty).or(error)).toBeVisible({ timeout: 15000 });

  // No uncaught app errors surfaced on mount / fetch when the inbox is empty.
  expect(consoleErrors).toEqual([]);
});

const project = (id: string, name: string) => ({
  id,
  name,
  slug: id,
  description: null,
  status: 'active',
  version: 1,
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
});

const json = (body: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify(body),
});

test('research view: aggregates research notes across projects ranked by confidence', async ({
  page,
}) => {
  const projects = [project('p1', 'Alpha'), project('p2', 'Beta')];
  // Notes across two projects with varied confidence, arranged so the expected
  // confidence-desc ranking interleaves the two projects:
  //   0.90 (p1, "Streaming ingestion") — highest
  //   0.70 (p2, "Vector store tradeoffs")
  //   0.40 (p1, "Legacy queue migration") — lowest
  // One note carries a freshness string; one carries a summary.
  const notesByProject: Record<string, unknown[]> = {
    p1: [
      {
        id: 'n-high', title: 'Streaming ingestion', confidence: 0.9,
        freshness: 'fresh',
        summary: 'Backpressure-aware pipeline evaluated against three brokers.',
        findings: ['Kafka wins on throughput', 'NATS wins on latency'],
        sources: ['https://kafka.apache.org', 'https://nats.io'],
      },
      {
        id: 'n-low', title: 'Legacy queue migration', confidence: 0.4,
        freshness: null, summary: null,
      },
    ],
    p2: [
      {
        id: 'n-mid', title: 'Vector store tradeoffs', confidence: 0.7,
        freshness: null, summary: null,
      },
    ],
  };

  await page.route('**/projects', (route) =>
    route.request().method() === 'GET' ? route.fulfill(json(projects)) : route.continue(),
  );
  await page.route('**/projects/*/research-notes', (route) => {
    if (route.request().method() !== 'GET') {
      return route.continue();
    }
    const match = /\/projects\/([^/]+)\/research-notes/.exec(route.request().url());
    const projectId = match ? match[1] : '';
    return route.fulfill(json(notesByProject[projectId] ?? []));
  });

  await page.goto('/');
  await navTo(page, 'research');

  const view = page.getByTestId('research-view');
  await expect(view).toBeVisible();

  const rows = page.getByTestId('research-note-card');
  await expect(rows).toHaveCount(3, { timeout: 15000 });

  // Count summary reflects total notes across both projects.
  await expect(page.getByTestId('research-count')).toHaveText(/3 notes across 2 projects/);

  // Confidence-desc ordering across the cards, interleaving projects.
  await expect(rows.nth(0)).toContainText('Streaming ingestion');
  await expect(rows.nth(1)).toContainText('Vector store tradeoffs');
  await expect(rows.nth(2)).toContainText('Legacy queue migration');

  // The highest-confidence note carries its freshness pill and summary.
  await expect(rows.nth(0).locator('.aos-pill.info')).toBeVisible();
  await expect(rows.nth(0)).toContainText('Backpressure-aware pipeline');

  // AOS-CONTRACT-001: findings + sources the backend records now render.
  await expect(rows.nth(0).getByTestId('research-note-findings')).toContainText('Kafka wins on throughput');
  await expect(rows.nth(0).getByTestId('research-note-sources')).toContainText('2 sources');
});
