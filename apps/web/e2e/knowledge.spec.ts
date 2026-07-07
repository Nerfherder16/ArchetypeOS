import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-KNOW-003 (RFC-0002 read surface): the GLOBAL Knowledge dashboard view.
// Knowledge is not project-scoped (lessons have no project), so this drives it
// with NO project selected. The committed vault (knowledge/wiki/lessons/index.md)
// is the source of truth; serve-api.sh exports KNOWLEDGE_ROOT so the in-harness
// POST /knowledge/sync finds it. Uniquely-named entities are unused here since
// the sync is idempotent over the shared serial API/db.
const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

test('knowledge: sync from vault surfaces lessons, open lesson badged, open filter, persistence', async ({
  page,
}) => {
  // A uid keeps the run distinguishable in traces even though sync is idempotent.
  void uid();

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  // Knowledge is its own rail view (global — no project needed).
  await navTo(page, 'knowledge');

  // Global surface: renders with no project selected.
  const knowledge = page
    .locator('section')
    .filter({ has: page.getByRole('heading', { name: 'Knowledge', exact: true }) });
  await expect(knowledge.getByRole('heading', { name: 'Knowledge', exact: true })).toBeVisible();
  const syncButton = knowledge.getByRole('button', { name: /sync from vault/i });
  await expect(syncButton).toBeVisible();

  // Sync populates the list from the committed vault.
  await syncButton.click();

  // At least one lesson carries the "open" badge. Assert generically against the
  // "(lesson · open)" badge rather than pinning a specific ID — a lesson's status
  // flips when a loop consumes it (AOS-20 closed LES-007, the former open anchor).
  const openLessonRow = knowledge.getByRole('listitem').filter({ hasText: /\(lesson · open\)/i }).first();
  await expect(openLessonRow).toBeVisible({ timeout: 15000 });
  // "Doc staleness" (LES-007) is present and is now a stable CLOSED anchor.
  const docStalenessRow = knowledge.getByRole('listitem').filter({ hasText: /Doc staleness/i });
  await expect(docStalenessRow).toBeVisible();
  await expect(docStalenessRow).toContainText(/closed/i);

  // At least the known lessons are listed (12+ in the seeded vault); assert a
  // healthy floor rather than an exact count to stay robust to vault growth.
  const allRows = knowledge.getByRole('listitem');
  expect(await allRows.count()).toBeGreaterThanOrEqual(12);
  // A known closed lesson (LES-001) is present under the default All filter.
  const closedLessonRow = knowledge.getByRole('listitem').filter({ hasText: /Credential-shaped strings/i });
  await expect(closedLessonRow).toBeVisible();

  // The returned counts render (e.g. "synced 12 · 1 open").
  await expect(knowledge.getByText(/synced \d+ · \d+ open/i)).toBeVisible();

  // Toggle to Open: an open lesson stays; known CLOSED lessons (LES-001
  // "Credential-shaped strings" and LES-007 "Doc staleness") drop. Asserted via
  // retrying web-first assertions (toBeVisible / toHaveCount(0)) so the async
  // refetch settles — and count-agnostic, since the open-lesson count grows as
  // lessons are recorded (append-only, LES-012).
  await knowledge.getByRole('button', { name: 'Open', exact: true }).click();
  await expect(openLessonRow).toBeVisible();
  await expect(closedLessonRow).toHaveCount(0);
  await expect(docStalenessRow).toHaveCount(0);

  // Reload persistence: the synced lessons survive (DB-backed read projection).
  // After reload the filter resets to All, so all lessons render again.
  await page.reload();
  await navTo(page, 'knowledge');
  const knowledgeAfter = page
    .locator('section')
    .filter({ has: page.getByRole('heading', { name: 'Knowledge', exact: true }) });
  await expect(
    knowledgeAfter.getByRole('listitem').filter({ hasText: /Doc staleness/i }),
  ).toBeVisible({ timeout: 15000 });
});
