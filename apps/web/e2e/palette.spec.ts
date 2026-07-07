import { expect, test } from '@playwright/test';

// AOS-UI-008 — neon command-deck palette migration. These assertions guard the
// theme SCOPING (the one behavioural risk of a values-level migration): the dark
// theme must carry the black→neon-red field, and toggling to light must reset it
// to a flat light ground. Token values, not pixels, so the checks are stable.

function tokens(page: import('@playwright/test').Page) {
  return page.locator('.aos-surface').first().evaluate((el) => {
    const s = getComputedStyle(el);
    return {
      glow: s.getPropertyValue('--shell-glow').trim(),
      ground: s.getPropertyValue('--ground').trim().toLowerCase(),
      red: s.getPropertyValue('--red').trim().toLowerCase(),
    };
  });
}

test('palette: dark theme carries the neon-red field', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  const t = await tokens(page);
  expect(t.ground).toBe('#0a0406'); // near-black command-deck ground
  expect(t.red).toBe('#ff2f4d'); // neon red accent
  expect(t.glow).not.toBe('none'); // the red radial field is present
  expect(t.glow.length).toBeGreaterThan(0);
});

test('palette: light theme resets the field to a flat light ground', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  await page.getByRole('button', { name: /switch to light theme/i }).click();

  const t = await tokens(page);
  expect(t.glow).toBe('none'); // no red field under light
  expect(t.ground).not.toBe('#0a0406'); // light ground, not the dark near-black
});
