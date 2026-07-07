import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-UI-009 — the Operations-mode home: the orb command deck.
// Covers: Operations lands on Command; the canvas renders; submitting a task
// routes to the expected agent and shows the speaking banner; and a
// prefers-reduced-motion viewer gets a static deck (no crash, no rAF loop).

test('command deck: Operations lands on Command with the constellation canvas', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Selecting Operations routes to its first live surface — Command.
  await page.getByTestId('mode-operations').click();
  await expect(page.getByTestId('mode-operations')).toHaveAttribute('aria-pressed', 'true');
  const commandNav = page.getByTestId('nav-command');
  await expect(commandNav).toBeVisible();
  await expect(commandNav).toHaveAttribute('aria-current', 'page');
  await expect(page.locator('.aos-crumb-view')).toHaveText('Command');

  // The deck and its canvas render.
  const deck = page.getByTestId('command-deck');
  await expect(deck).toBeVisible();
  await expect(deck.locator('canvas')).toBeVisible();
  // Routing starts on standby; no one is speaking yet.
  await expect(page.getByTestId('command-routing')).toHaveText('STANDBY');
  await expect(page.getByTestId('command-speaking')).toHaveCount(0);
});

test('command deck: submitting a task routes to the expected agent and shows the speaking banner', async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => consoleErrors.push(err.message));

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await navTo(page, 'command');

  await expect(page.getByTestId('command-deck')).toBeVisible();

  // A guardian-shaped task routes deterministically to GUARDIAN (routeForTask).
  await page.getByTestId('command-input').fill('run the guardian gate on pr 92');
  await page.getByTestId('command-send').click();

  await expect(page.getByTestId('command-routing')).toHaveText('GUARDIAN');
  const speaking = page.getByTestId('command-speaking');
  await expect(speaking).toBeVisible();
  await expect(speaking).toContainText('GUARDIAN');

  // A quick-action chip also routes — Research → LIBRARIAN.
  await page.getByTestId('command-quick-research').click();
  await expect(page.getByTestId('command-routing')).toHaveText('LIBRARIAN');

  // No uncaught errors surfaced during route/speak.
  expect(consoleErrors).toEqual([]);
});

test('command deck: prefers-reduced-motion renders a static deck and still routes', async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await navTo(page, 'command');

  const deck = page.getByTestId('command-deck');
  await expect(deck).toBeVisible();
  await expect(deck.locator('canvas')).toBeVisible();

  // Even under reduced motion the console still routes deterministically.
  await page.getByTestId('command-input').fill('threat model the exposed api surface');
  await page.getByTestId('command-send').click();
  await expect(page.getByTestId('command-routing')).toHaveText('SECURITY');
});
