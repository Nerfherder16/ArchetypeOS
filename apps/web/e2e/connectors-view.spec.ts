import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-CONNECTOR-001 (UI) — the Connectors tab under Operations → Providers & Model
// Routing (eval Finding 9). Covers: the tab switches the panel; connectors render
// with privacy posture (privacy class, browser-exposed labeling) and health;
// unconfigured connectors are visible without erroring; and the panel degrades
// gracefully when the registry is unreachable. GET /connectors is mocked so the
// governance panel is deterministic.

const CONNECTORS = [
  {
    id: 'conn-1',
    name: 'sotto_stt',
    connector_type: 'stt',
    tier: 'local',
    enabled: true,
    configured: true,
    privacy_class: 'private_ok',
    egress_allowed: false,
    browser_exposed: true,
    quota_policy: 'self-hosted',
    last_health_status: 'healthy',
    last_error: null,
    last_checked_at: '2026-07-08T00:00:00Z',
    status: 'active',
    version: 1,
    created_at: '2026-07-08T00:00:00Z',
    updated_at: '2026-07-08T00:00:00Z',
  },
  {
    id: 'conn-2',
    name: 'exa',
    connector_type: 'research',
    tier: 'external',
    enabled: true,
    configured: false,
    privacy_class: 'public_only',
    egress_allowed: true,
    browser_exposed: false,
    quota_policy: 'metered',
    last_health_status: 'unknown',
    last_error: null,
    last_checked_at: null,
    status: 'active',
    version: 1,
    created_at: '2026-07-08T00:00:00Z',
    updated_at: '2026-07-08T00:00:00Z',
  },
];

test('connectors tab: renders governance posture, health and unconfigured connectors', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(err.message));

  await page.route('**/connectors', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CONNECTORS) });
  });

  await page.goto('/');
  await navTo(page, 'providers');

  // Switch from the Usage panel to the Connectors panel.
  await page.getByTestId('providers-tab-connectors').click();
  const view = page.getByTestId('connectors-view');
  await expect(view).toBeVisible();
  await expect(page.getByTestId('connectors-count')).toHaveText('1/2 configured');

  const cards = page.getByTestId('connector-card');
  await expect(cards).toHaveCount(2);

  // Sotto: healthy, private-ok, browser-exposed labeled.
  const sotto = page.locator('[data-connector="sotto_stt"]');
  await expect(sotto.getByTestId('connector-health')).toHaveText('healthy');
  await expect(sotto.getByTestId('connector-privacy')).toHaveText('private-ok');
  await expect(sotto.getByTestId('connector-browser-exposed')).toBeVisible();

  // Exa: unconfigured but still visible, marked unconfigured, public-only.
  const exa = page.locator('[data-connector="exa"]');
  await expect(exa.getByTestId('connector-unconfigured')).toBeVisible();
  await expect(exa.getByTestId('connector-privacy')).toHaveText('public-only');

  expect(consoleErrors).toEqual([]);
});

test('connectors tab: surfaces a registry error without crashing', async ({ page }) => {
  await page.route('**/connectors', async (route) => {
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) });
  });

  await page.goto('/');
  await navTo(page, 'providers');
  await page.getByTestId('providers-tab-connectors').click();
  await expect(page.getByTestId('connectors-error')).toBeVisible();
});
