import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-VOICE-003 — the Voice Inbox review queue under Operations. Covers: the
// nav surface routes to the view; captured turns render as review-first cards;
// and Approve transitions a pending item via PATCH /voice/inbox/{id}. The inbox
// GET + PATCH are mocked so the queue is deterministic regardless of server state.

const ITEM = {
  id: 'vi-e2e-1',
  project_id: null,
  transcript: 'research the best message queue for us',
  summary: 'Wants a survey of message queues.',
  detected_intent: 'research_request',
  detected_project: null,
  suggested_action: 'Draft a research task for the Research Librarian.',
  confidence: 0.9,
  required_review: true,
  review_state: 'pending',
  source_device: 'command-deck',
  reply_text: 'On it, drafting a research task for review.',
  promoted_kind: null,
  promoted_id: null,
  created_at: '2026-07-08T00:00:00Z',
};

test('voice inbox: renders captured turns and approves a pending item', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  await page.route('**/voice/inbox', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([ITEM]) });
  });
  await page.route('**/voice/inbox/vi-e2e-1', async (route) => {
    // PATCH → the item flipped to approved and promoted to a research note.
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ...ITEM, review_state: 'approved', promoted_kind: 'research_note', promoted_id: 'rn-1' }),
    });
  });

  await page.goto('/');
  await navTo(page, 'voice-inbox');

  const view = page.getByTestId('voice-inbox-view');
  await expect(view).toBeVisible();
  await expect(page.getByTestId('voice-inbox-count')).toHaveText('1 pending');

  const card = page.getByTestId('voice-inbox-card');
  await expect(card).toContainText('research the best message queue');
  await expect(card).toContainText('research request');

  await page.getByTestId('voice-inbox-approve').click();
  // Approve resolves the card to the approved state and shows the promotion badge.
  await expect(page.getByTestId('voice-inbox-state')).toHaveText('approved');
  await expect(page.getByTestId('voice-inbox-promoted')).toContainText('research note');

  expect(consoleErrors).toEqual([]);
});

test('voice inbox: shows the empty state when nothing is captured', async ({ page }) => {
  await page.route('**/voice/inbox', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });

  await page.goto('/');
  await navTo(page, 'voice-inbox');
  await expect(page.getByTestId('voice-inbox-empty')).toBeVisible();
});
