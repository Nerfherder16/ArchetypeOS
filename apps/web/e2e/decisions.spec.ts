import { expect, test } from '@playwright/test';

// Promoted from scripts/web_drive/drive_dec.mjs (AOS-DEC-001, PR #34).
// Uniquely-named entities keep serial reuse of the single shared API/db safe.
const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

test('decisions & research: create note, link a decision, confirm typed evidence', async ({
  page,
}) => {
  const projectName = `Decisions Verify ${uid()}`;
  const noteTitle = `Postgres vs SQLite tradeoffs ${uid()}`;
  const decisionTitle = `Keep dual-database posture ${uid()}`;

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  await page.getByPlaceholder('New project name').fill(projectName);
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page.getByRole('button', { name: projectName })).toBeVisible();

  // Selecting the project reveals the Decisions & Research section.
  await expect(page.getByRole('heading', { name: 'Decisions & Research' })).toBeVisible();

  // Create a research note via the form.
  await page.getByPlaceholder('Research note title').fill(noteTitle);
  await page.getByPlaceholder('Summary').fill('Postgres for runtime, SQLite for tests.');
  await page.getByRole('button', { name: /add research note/i }).click();
  // The title also appears in the decision's <select> options, so scope to the
  // Research Notes list item.
  await expect(page.getByRole('listitem').filter({ hasText: noteTitle })).toBeVisible();

  // Create a decision linked to the note via the select (index 1 = the note).
  await page.getByPlaceholder('Decision title').fill(decisionTitle);
  await page.getByPlaceholder('Decision text').fill('Postgres in compose, SQLite in tests, per research.');
  await page.locator('select').last().selectOption({ index: 1 });
  await page.getByRole('button', { name: /add decision/i }).click();
  await expect(page.getByText(decisionTitle)).toBeVisible();

  // The decision row reports one linked research note.
  await expect(page.getByText(/1 linked research/)).toBeVisible();

  // Reload persistence.
  await page.reload();
  await page.getByRole('button', { name: projectName }).first().click();
  await expect(page.getByText(decisionTitle)).toBeVisible();
  await expect(page.getByRole('listitem').filter({ hasText: noteTitle })).toBeVisible();

  // API-level confirmation of the typed evidence link on this project's decision.
  const evidence = await page.evaluate(async (name) => {
    const projects = await (await fetch('http://localhost:8000/projects')).json();
    const project = projects.find((p: { name: string }) => p.name === name);
    if (!project) return [];
    const decisions = await (
      await fetch(`http://localhost:8000/projects/${project.id}/decisions`)
    ).json();
    return decisions[0]?.evidence ?? [];
  }, projectName);
  expect(
    evidence.some((e: { type?: string; id?: string }) => e && e.type === 'research_note' && e.id),
  ).toBe(true);
});
