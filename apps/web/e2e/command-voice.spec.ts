import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-VOICE-002 — the CommandDeck routes a typed or spoken command through the
// Voice Command Center backend (POST /voice/turns) and surfaces the spoken
// reply. Covers the typed round-trip (mocked so the reply is deterministic
// regardless of the server's LLM provider) and the Sotto-not-configured mic
// fallback. The mic/WebSocket streaming path itself is verified at deploy time
// against the live Sotto server.

test('command deck: a typed command routes through /voice/turns and shows the reply', async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  await page.route('**/voice/turns', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'voice-e2e-1',
        project_id: null,
        transcript: 'research the best queue',
        summary: 'Wants a survey of message queues.',
        detected_intent: 'research_request',
        detected_project: null,
        suggested_action: 'Draft a research task.',
        confidence: 0.9,
        required_review: true,
        review_state: 'pending',
        source_device: 'command-deck',
        reply_text: 'On it, drafting a research task for review.',
        created_at: '2026-07-08T00:00:00Z',
      }),
    });
  });

  await page.goto('/');
  await navTo(page, 'command');
  await expect(page.getByTestId('command-deck')).toBeVisible();

  await page.getByTestId('command-input').fill('research the best queue');
  await page.getByTestId('command-send').click();

  // Orb routing fires synchronously (routeForTask → LIBRARIAN).
  await expect(page.getByTestId('command-routing')).toHaveText('LIBRARIAN');
  // The backend reply is surfaced in the console reply line.
  await expect(page.locator('.cmd-reply')).toContainText('drafting a research task');

  expect(consoleErrors).toEqual([]);
});

test('command deck: mic reports voice unavailable when Sotto is not configured', async ({ page }) => {
  await page.goto('/');
  await navTo(page, 'command');
  await expect(page.getByTestId('command-deck')).toBeVisible();

  // No VITE_SOTTO_WS_URL in the e2e build → tapping the mic degrades gracefully.
  await page.getByTestId('command-mic').click();
  await expect(page.locator('.cmd-reply')).toContainText('voice unavailable');
});
