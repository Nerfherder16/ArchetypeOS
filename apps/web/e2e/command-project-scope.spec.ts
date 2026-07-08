import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-VOICE-PROJECT-001 — the CommandDeck scopes voice/command turns to the
// selected project (so promotion into a research note / decision works), and
// labels project-scoped vs global capture. Mocks keep it hermetic.

const PROJECT = { id: 'proj-scope-1', name: 'Recall', slug: 'recall', status: 'active', version: 1, created_at: '2026-07-08T00:00:00Z', updated_at: '2026-07-08T00:00:00Z' };

const TURN = {
  id: 'vi-scope-1', project_id: PROJECT.id, transcript: 'research the best vector db',
  summary: 's', detected_intent: 'research_request', detected_project: null,
  suggested_action: 'Draft a research task.', confidence: 0.9, required_review: true,
  review_state: 'pending', source_device: 'command-deck', reply_text: 'On it.',
  promoted_kind: null, promoted_id: null, created_at: '2026-07-08T00:00:00Z',
};

test('command deck: global capture by default, project-scoped after selecting a project', async ({ page }) => {
  let lastBody: Record<string, unknown> | null = null;
  await page.route('**/projects', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([PROJECT]) });
    } else {
      await route.fallback();
    }
  });
  await page.route('**/voice/turns', async (route) => {
    lastBody = route.request().postDataJSON();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(TURN) });
  });
  await page.route('**/voice/speak', (route) => route.fulfill({ status: 204, body: '' }));

  await page.goto('/');

  // Default: no project selected → global capture.
  await navTo(page, 'command');
  await expect(page.getByTestId('command-scope')).toContainText('global capture');

  // Select the project from the rail, return to Command → scope shows the project.
  await page.getByRole('button', { name: /Recall — active/ }).click();
  await navTo(page, 'command');
  await expect(page.getByTestId('command-scope')).toContainText('Recall');

  // A submitted command now carries the project id.
  await page.getByTestId('command-input').fill('research the best vector db');
  await page.getByTestId('command-send').click();
  await expect.poll(() => lastBody?.project_id).toBe(PROJECT.id);
  expect(lastBody?.source_device).toBe('command-deck');
});
