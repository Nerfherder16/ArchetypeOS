import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-GOV-001 — the Council "Approvals & Authority" surface is now a LIVE
// "Awaiting You" governance queue backed by the existing decision endpoints
// (GET /projects, per-project GET /projects/{id}/decisions, POST
// /decisions/{id}/approve|reject). The e2e harness boots a real API against a
// fresh, empty sqlite DB (no seeded projects), so the aggregated queue resolves
// to its graceful EMPTY state — never a hang, throw, or white screen. Harness
// conventions mirror providers-view.spec.ts.

test('approvals view: Council surface is live and mounts the governance queue', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    // Ignore the dev server's favicon.ico 404 — a static-asset quirk of the
    // Vite preview origin, not an app or API error. We only care that mounting
    // the view with an absent/empty backend surfaces no app-level errors.
    if (msg.type() === 'error' && !msg.location().url.endsWith('/favicon.ico')) {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => consoleErrors.push(err.message));

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Council mode reveals its surfaces. "Awaiting You" (was "Approvals &
  // Authority") is now a live nav item (nav-approvals), not a disabled `soon-*`
  // stub. The stable surface id is kept, so the old soon-* testid is gone.
  await page.getByTestId('mode-council').click();
  const approvalsNav = page.getByTestId('nav-approvals');
  await expect(approvalsNav).toBeVisible();
  await expect(approvalsNav).toHaveText(/Awaiting You/);
  await expect(page.getByTestId('soon-approvals-authority')).toHaveCount(0);

  // Route to it via the shared nav helper (selects the owning mode, clicks nav).
  await navTo(page, 'approvals');

  // The view mounts with its heading even when no data is seeded.
  const view = page.getByTestId('approvals-view');
  await expect(view).toBeVisible();
  await expect(view.getByText('Decisions awaiting your approval')).toBeVisible();

  // Resolves to a terminal graceful surface: EITHER a seeded pending card, the
  // empty state (fresh DB), OR a readable error notice (API down) — never a
  // hang. `.or()` yields the first that matches; the assertion retries (LES-015:
  // never a one-shot `.count()`).
  const card = page.getByTestId('approval-card').first();
  const empty = page.getByTestId('approvals-empty');
  const error = page.getByTestId('approvals-error');
  await expect(card.or(empty).or(error)).toBeVisible({ timeout: 15000 });

  // If the harness seeded pending decisions, a needs_evidence card's Approve is
  // disabled with the evidence reason; a draft card's Approve is enabled.
  if (await card.isVisible()) {
    const blocked = page.locator('[data-testid="approval-card"][data-status="needs_evidence"]').first();
    if (await blocked.isVisible()) {
      await expect(blocked.getByTestId('approval-approve')).toBeDisabled();
      await expect(blocked.getByTestId('approval-blocked-reason')).toBeVisible();
    }
    const draft = page.locator('[data-testid="approval-card"][data-status="draft"]').first();
    if (await draft.isVisible()) {
      await expect(draft.getByTestId('approval-approve')).toBeEnabled();
    }
    // Reject is offered on every pending card.
    await expect(card.getByTestId('approval-reject')).toBeVisible();
  }

  // No uncaught app errors surfaced on mount / fetch when the queue is empty.
  expect(consoleErrors).toEqual([]);
});
