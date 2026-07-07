import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-USAGE-002 — the Operations "Providers & Model Routing" surface is now a
// LIVE usage view backed by GET /usage/summary (AOS-USAGE-001). The e2e harness
// boots a real API against a fresh, empty ledger, so the view resolves to its
// graceful EMPTY state (no seeded usage) — never a hang, throw, or white screen.
// Harness conventions mirror command-home.spec.ts.

test('providers view: Operations surface is live and mounts the usage view', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => consoleErrors.push(err.message));

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Operations mode reveals its surfaces. "Providers & Model Routing" is now a
  // live nav item (nav-providers), not a disabled `soon-*` stub.
  await page.getByTestId('mode-operations').click();
  const providersNav = page.getByTestId('nav-providers');
  await expect(providersNav).toBeVisible();
  await expect(page.getByTestId('soon-providers-routing')).toHaveCount(0);

  // Route to it via the shared nav helper (selects the owning mode, clicks nav).
  await navTo(page, 'providers');

  // The view mounts with its heading + window selector even with no seeded data.
  const view = page.getByTestId('providers-view');
  await expect(view).toBeVisible();
  await expect(view.getByText('LLM usage across your tiers')).toBeVisible();
  await expect(page.getByTestId('providers-window-today')).toBeVisible();
  await expect(page.getByTestId('providers-window-7d')).toBeVisible();
  await expect(page.getByTestId('providers-window-30d')).toBeVisible();

  // Default window is 7d (pressed).
  await expect(page.getByTestId('providers-window-7d')).toHaveAttribute('aria-pressed', 'true');

  // Resolves to a terminal graceful surface — EITHER the empty state (fresh
  // ledger) OR a readable error notice (API down) — never a hang.
  const empty = page.getByTestId('providers-empty');
  const error = page.getByTestId('providers-error');
  await expect(empty.or(error)).toBeVisible({ timeout: 15000 });

  // No uncaught errors surfaced on mount / fetch when the ledger is empty.
  expect(consoleErrors).toEqual([]);
});

test('providers view: switching the window control re-fetches and stays graceful', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await navTo(page, 'providers');

  const view = page.getByTestId('providers-view');
  await expect(view).toBeVisible();

  // Terminal state on the default window first.
  const terminal = page.getByTestId('providers-empty').or(page.getByTestId('providers-error'));
  await expect(terminal).toBeVisible({ timeout: 15000 });

  // Switch to 30d — the control updates its pressed state (re-fetch issued) and
  // the view resolves to a graceful terminal state again.
  await page.getByTestId('providers-window-30d').click();
  await expect(page.getByTestId('providers-window-30d')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByTestId('providers-window-7d')).toHaveAttribute('aria-pressed', 'false');
  await expect(terminal).toBeVisible({ timeout: 15000 });

  // And back to Today.
  await page.getByTestId('providers-window-today').click();
  await expect(page.getByTestId('providers-window-today')).toHaveAttribute('aria-pressed', 'true');
  await expect(terminal).toBeVisible({ timeout: 15000 });
});
