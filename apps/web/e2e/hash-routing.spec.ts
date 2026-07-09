import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-WEB-SPINE-001 (slice 1) — URL-hash routing for the active view. Covers:
// deep-linking (loading `#/<view>` mounts that view), that in-app navigation
// writes the hash, that an unknown hash falls back to the default, and that the
// browser back button navigates between views. GET /nodes is mocked so the
// deep-linked Nodes view resolves deterministically.

test('hash routing: deep-linking #/nodes mounts the Nodes view directly', async ({ page }) => {
  await page.route('**/nodes', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });

  await page.goto('/#/nodes');
  await expect(page.getByTestId('nodes-view')).toBeVisible();
});

test('hash routing: an unknown hash falls back to the default view', async ({ page }) => {
  await page.goto('/#/does-not-exist');
  // Falls back to Overview (the default); the shell still mounts, no white screen.
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await expect(page.getByTestId('nodes-view')).toHaveCount(0);
});

test('hash routing: in-app navigation writes the hash to the rail', async ({ page }) => {
  await page.goto('/');
  // Navigating via the rail writes the view into the URL hash (deep-linkable).
  await navTo(page, 'providers');
  await expect(page.getByTestId('providers-view')).toBeVisible();
  await expect(page).toHaveURL(/#\/providers$/);
});

test('hash routing: a hash change (back/forward, manual) drives the view', async ({ page }) => {
  await page.route('**/nodes', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });

  await page.goto('/#/nodes');
  await expect(page.getByTestId('nodes-view')).toBeVisible();

  // A direct hash change (as the address bar or a link would produce) pushes one
  // history entry and switches the view — the external-hash path.
  await page.evaluate(() => {
    window.location.hash = '#/providers';
  });
  await expect(page.getByTestId('providers-view')).toBeVisible();

  // Browser back returns to the Nodes view (history is hash-driven).
  await page.goBack();
  await expect(page.getByTestId('nodes-view')).toBeVisible();
  await expect(page).toHaveURL(/#\/nodes$/);
});
