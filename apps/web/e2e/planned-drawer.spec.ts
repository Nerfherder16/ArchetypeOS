import { expect, test } from '@playwright/test';

// AOS-UX-IA-001 (deliverable 2) — the Planned drawer. Clicking a "soon" surface
// in the rail (previously a dead disabled chip) opens a drawer describing what
// the planned surface is intended to be. Mock-free: it reads static planned data.

test('planned drawer: clicking a "soon" surface opens it with summary + phase', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Switch to the Research mode, which has planned surfaces.
  await page.getByTestId('mode-research').click();

  // Closed by default.
  await expect(page.getByTestId('planned-drawer')).toHaveCount(0);

  // Click the planned "Knowledge Graph" surface.
  await page.getByTestId('soon-knowledge-graph').click();

  const drawer = page.getByTestId('planned-drawer');
  await expect(drawer).toBeVisible();
  await expect(page.getByTestId('planned-drawer-title')).toHaveText('Knowledge Graph');
  await expect(page.getByTestId('planned-drawer-badge')).toHaveText('Planned');
  await expect(page.getByTestId('planned-drawer-summary')).toContainText('knowledge graph');
  await expect(page.getByTestId('planned-drawer-phase')).toBeVisible();
});

test('planned drawer: Escape and the close button dismiss it', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await page.getByTestId('mode-research').click();

  // Open, then close with Escape.
  await page.getByTestId('soon-distillation').click();
  await expect(page.getByTestId('planned-drawer')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('planned-drawer')).toHaveCount(0);

  // Open again, close with the Close button.
  await page.getByTestId('soon-distillation').click();
  await expect(page.getByTestId('planned-drawer')).toBeVisible();
  await page.getByTestId('planned-drawer-close').click();
  await expect(page.getByTestId('planned-drawer')).toHaveCount(0);
});

test('planned drawer: switching surfaces updates the drawer content', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();
  await page.getByTestId('mode-council').click();

  await page.getByTestId('soon-final-judge').click();
  await expect(page.getByTestId('planned-drawer-title')).toHaveText('Final Judge');

  // Backdrop-close, then open a different planned surface.
  await page.getByTestId('planned-drawer-backdrop').click({ position: { x: 5, y: 5 } });
  await expect(page.getByTestId('planned-drawer')).toHaveCount(0);

  await page.getByTestId('soon-orchestration').click();
  await expect(page.getByTestId('planned-drawer-title')).toHaveText('Orchestration');
});
