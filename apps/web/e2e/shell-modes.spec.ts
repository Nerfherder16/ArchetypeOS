import { expect, test } from '@playwright/test';

// AOS-UI-007 — workspace-mode shell + resolution-adaptive layout.
// Drives the rail's mode switcher, the per-mode surface list (live nav buttons +
// disabled "soon" chips), the Builder coming-soon empty state, and the responsive
// tiers (phone bottom tab bar vs desktop rail). No project is required — these
// assertions are about the shell chrome, not view data.

test('shell modes: default lands on Overview with Executive mode active', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Executive is the mode owning Overview; it is pressed by default.
  await expect(page.getByTestId('mode-executive')).toHaveAttribute('aria-pressed', 'true');
  // Overview is the active surface.
  const overviewNav = page.getByTestId('nav-overview');
  await expect(overviewNav).toBeVisible();
  await expect(overviewNav).toHaveAttribute('aria-current', 'page');
  // Breadcrumb shows the mode + view.
  await expect(page.locator('.aos-crumb-mode')).toHaveText('Executive');
  await expect(page.locator('.aos-crumb-view')).toHaveText('Overview');
});

test('shell modes: selecting Architect reveals its surfaces and routes to Repositories', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  await page.getByTestId('mode-architect').click();

  // The Architect mode is now pressed; its three live surfaces are present.
  await expect(page.getByTestId('mode-architect')).toHaveAttribute('aria-pressed', 'true');
  const reposNav = page.getByTestId('nav-repositories');
  await expect(reposNav).toBeVisible();
  await expect(page.getByTestId('nav-architecture')).toBeVisible();
  await expect(page.getByTestId('nav-reuse')).toBeVisible();

  // Selecting a mode with a live surface routes the workspace to its first live
  // view (Repositories), which becomes the active surface.
  await expect(reposNav).toHaveAttribute('aria-current', 'page');
});

test('shell modes: a planned surface renders as a disabled "soon" item', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  await page.getByTestId('mode-research').click();

  const soon = page.getByTestId('soon-research-inbox');
  await expect(soon).toBeVisible();
  await expect(soon).toBeDisabled();
  await expect(soon).toHaveAttribute('aria-disabled', 'true');
});

test('shell modes: Builder (no live surface) shows the coming-soon empty state', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  await page.getByTestId('mode-builder').click();

  await expect(page.getByTestId('mode-builder')).toHaveAttribute('aria-pressed', 'true');
  const empty = page.getByTestId('workspace-empty');
  await expect(empty).toBeVisible();
  await expect(empty.getByText(/coming soon/i)).toBeVisible();
  // No live surface means no nav-<view> button for a Builder view.
  await expect(page.getByTestId('nav-overview')).toHaveCount(0);
});

test('shell modes: layout adapts — phone bottom tab bar vs wide rail, no h-overflow', async ({
  page,
}) => {
  // Phone tier: the mode switcher pins to a fixed bottom tab bar.
  await page.setViewportSize({ width: 390, height: 780 });
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  const modebarPosition = await page
    .locator('.aos-modebar')
    .evaluate((el) => getComputedStyle(el).position);
  expect(modebarPosition).toBe('fixed');
  await expect(page.getByTestId('mode-operations')).toBeVisible();

  const phoneOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(phoneOverflow).toBe(false);

  // Wide tier: the left rail is present and static (not a fixed bottom bar).
  await page.setViewportSize({ width: 2560, height: 1080 });
  await expect(page.locator('.aos-rail')).toBeVisible();
  const wideModebarPosition = await page
    .locator('.aos-modebar')
    .evaluate((el) => getComputedStyle(el).position);
  expect(wideModebarPosition).toBe('static');

  const wideOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(wideOverflow).toBe(false);
});
