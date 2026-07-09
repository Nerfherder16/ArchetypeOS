import { expect, test } from '@playwright/test';

// AOS-UX-IA-001 (deliverable 1) — the global command palette. Opens with
// Cmd/Ctrl+K, filters the live surfaces as you type, Enter navigates to the
// highlighted surface (URL-routed), and Escape closes it. Mock-free: it drives
// only the shell's own navigation, asserted on the URL hash + rail state.

test('command palette: Cmd/Ctrl+K opens it, typing filters, Enter navigates', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Closed by default.
  await expect(page.getByTestId('command-palette')).toHaveCount(0);

  // Open with the keyboard shortcut (cross-platform).
  await page.keyboard.press('ControlOrMeta+KeyK');
  await expect(page.getByTestId('command-palette')).toBeVisible();
  await expect(page.getByTestId('command-palette-input')).toBeFocused();

  // Typing filters the surface list down to the Reuse surface.
  await page.getByTestId('command-palette-input').fill('reuse');
  const items = page.getByTestId('command-palette-item');
  await expect(items).toHaveCount(1);
  await expect(items.first()).toContainText('Reuse');

  // Enter navigates to it (URL-routed) and closes the palette.
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#\/reuse$/);
  await expect(page.getByTestId('command-palette')).toHaveCount(0);
});

test('command palette: a non-matching query shows the empty state', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await page.keyboard.press('ControlOrMeta+KeyK');
  await page.getByTestId('command-palette-input').fill('zzzznotasurface');
  await expect(page.getByTestId('command-palette-empty')).toBeVisible();
  await expect(page.getByTestId('command-palette-item')).toHaveCount(0);
});

test('command palette: Escape closes it without navigating', async ({ page }) => {
  await page.goto('/#/overview');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await page.keyboard.press('ControlOrMeta+KeyK');
  await expect(page.getByTestId('command-palette')).toBeVisible();

  await page.getByTestId('command-palette-input').fill('nodes');
  await page.keyboard.press('Escape');

  await expect(page.getByTestId('command-palette')).toHaveCount(0);
  // Still on Overview — Escape must not navigate.
  await expect(page).toHaveURL(/#\/overview$/);
});

test('command palette: clicking the backdrop closes it', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await page.keyboard.press('ControlOrMeta+KeyK');
  await expect(page.getByTestId('command-palette')).toBeVisible();

  // Click the backdrop (outside the dialog) to dismiss.
  await page.getByTestId('command-palette-backdrop').click({ position: { x: 5, y: 5 } });
  await expect(page.getByTestId('command-palette')).toHaveCount(0);
});
