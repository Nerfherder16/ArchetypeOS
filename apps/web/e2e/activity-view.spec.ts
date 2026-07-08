import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-OPS-002 — the Operations "Live Activity" surface is now a LIVE feed that
// aggregates the platform's Jobs (scans, digests, council reviews, scheduled
// runs) across all projects into one time-ordered stream. Frontend only — it
// composes the existing GET /projects + per-project GET /projects/{id}/jobs
// endpoints. The first test uses the real API booted by the harness against a
// fresh, empty sqlite DB (no seeded projects), so the aggregated feed resolves
// to its graceful EMPTY state — never a hang, throw, or white screen. The second
// route-stubs projects + jobs to assert rows render newest-first with the right
// status pills incl. a failed row. Harness conventions mirror
// providers-view.spec.ts / council-agent-model.spec.ts.

test('activity view: Operations surface is live and mounts the feed gracefully', async ({ page }) => {
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

  // Operations mode reveals its surfaces. "Live Activity" is now a live nav item
  // (nav-activity), not a disabled `soon-*` stub. The stable surface id is kept,
  // so the old soon-* testid is gone.
  await page.getByTestId('mode-operations').click();
  const activityNav = page.getByTestId('nav-activity');
  await expect(activityNav).toBeVisible();
  await expect(activityNav).toHaveText(/Live Activity/);
  await expect(page.getByTestId('soon-live-activity')).toHaveCount(0);

  // Route to it via the shared nav helper (selects the owning mode, clicks nav).
  await navTo(page, 'activity');

  // The view mounts with its heading even when no data is seeded.
  const view = page.getByTestId('activity-view');
  await expect(view).toBeVisible();
  await expect(view.getByText('System activity feed')).toBeVisible();

  // Resolves to a terminal graceful surface: EITHER seeded rows, the empty state
  // (fresh DB), OR a readable error notice (API down) — never a hang. `.or()`
  // yields the first that matches; the assertion retries (LES-015: never a
  // one-shot `.count()`).
  const row = page.getByTestId('activity-row').first();
  const empty = page.getByTestId('activity-empty');
  const error = page.getByTestId('activity-error');
  await expect(row.or(empty).or(error)).toBeVisible({ timeout: 15000 });

  // No uncaught app errors surfaced on mount / fetch when the feed is empty.
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

test('activity view: aggregates jobs across projects newest-first with status pills', async ({
  page,
}) => {
  const projects = [project('p1', 'Alpha'), project('p2', 'Beta')];
  // Jobs across two projects with varied job_type + status. Ordering key is
  // finished_at ?? started_at ?? queued_at — arranged so the expected newest→
  // oldest order is: j-done (p1, 12:00:30 finished), j-run (p2, 11:00:10
  // started), j-fail (p1, 10:00:05 finished), j-queued (p2, 09:00:00 queued).
  const jobsByProject: Record<string, unknown[]> = {
    p1: [
      {
        id: 'j-done', job_type: 'council_review', status: 'done', attempts: 1,
        project_id: 'p1', repository_id: null, error: null,
        queued_at: '2026-07-07T12:00:00Z', started_at: '2026-07-07T12:00:10Z',
        finished_at: '2026-07-07T12:00:30Z',
      },
      {
        id: 'j-fail', job_type: 'repository_scan', status: 'failed', attempts: 3,
        project_id: 'p1', repository_id: 'r1', error: 'clone timed out after 3 attempts',
        queued_at: '2026-07-07T10:00:00Z', started_at: '2026-07-07T10:00:01Z',
        finished_at: '2026-07-07T10:00:05Z',
      },
    ],
    p2: [
      {
        id: 'j-run', job_type: 'project_digest', status: 'running', attempts: 1,
        project_id: 'p2', repository_id: null, error: null,
        queued_at: '2026-07-07T11:00:00Z', started_at: '2026-07-07T11:00:10Z',
        finished_at: null,
      },
      {
        id: 'j-queued', job_type: 'repository_scan', status: 'queued', attempts: 0,
        project_id: 'p2', repository_id: 'r2', error: null,
        queued_at: '2026-07-07T09:00:00Z', started_at: null, finished_at: null,
      },
    ],
  };

  await page.route('**/projects', (route) =>
    route.request().method() === 'GET' ? route.fulfill(json(projects)) : route.continue(),
  );
  await page.route('**/projects/*/jobs', (route) => {
    if (route.request().method() !== 'GET') {
      return route.continue();
    }
    const match = /\/projects\/([^/]+)\/jobs/.exec(route.request().url());
    const projectId = match ? match[1] : '';
    return route.fulfill(json(jobsByProject[projectId] ?? []));
  });

  await page.goto('/');
  await navTo(page, 'activity');

  const view = page.getByTestId('activity-view');
  await expect(view).toBeVisible();

  const rows = page.getByTestId('activity-row');
  await expect(rows).toHaveCount(4, { timeout: 15000 });

  // Count summary reflects total events across both projects.
  await expect(page.getByTestId('activity-count')).toHaveText(/4 events across 2 projects/);

  // Newest-first ordering by finished ?? started ?? queued.
  await expect(rows.nth(0)).toHaveAttribute('data-status', 'done');
  await expect(rows.nth(1)).toHaveAttribute('data-status', 'running');
  await expect(rows.nth(2)).toHaveAttribute('data-status', 'failed');
  await expect(rows.nth(3)).toHaveAttribute('data-status', 'queued');

  // Status pills carry the defensive tier map (good / info / risk / neutral).
  await expect(rows.nth(0).locator('.aos-pill.good')).toBeVisible();
  await expect(rows.nth(1).locator('.aos-pill.info')).toBeVisible();
  await expect(rows.nth(2).locator('.aos-pill.risk')).toBeVisible();
  await expect(rows.nth(3).locator('.aos-pill.neutral')).toBeVisible();

  // Human-labeled job_type + project provenance render.
  await expect(rows.nth(0)).toContainText('Council review');
  await expect(rows.nth(0)).toContainText('Alpha');

  // The failed row shows its error snippet.
  await expect(rows.nth(2)).toContainText('clone timed out after 3 attempts');
});
