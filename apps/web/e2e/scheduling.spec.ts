import { expect, test } from '@playwright/test';
import { navTo } from './support/nav';

// AOS-SCHED-002 (RFC-0007 Phase 3b): the Scheduling & Jobs control surface.
// Uniquely-named entities keep serial reuse of the single shared API/db safe.
const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

test('scheduling & jobs: create a schedule, run it now, see the job in history', async ({
  page,
}) => {
  const projectName = `Scheduling Verify ${uid()}`;
  const scheduleName = `Nightly digest ${uid()}`;

  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  await page.getByPlaceholder('New project name').fill(projectName);
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page.getByRole('button', { name: projectName })).toBeVisible();

  // Scheduling & Jobs is its own rail view.
  await navTo(page, 'scheduling');
  await expect(page.getByRole('heading', { name: 'Scheduling & Jobs' })).toBeVisible();
  await expect(page.getByText('No schedules yet.')).toBeVisible();

  // Create a project_digest schedule via the form.
  await page.getByPlaceholder('Schedule name').fill(scheduleName);
  await page
    .getByRole('combobox')
    .filter({ has: page.getByRole('option', { name: 'project_digest' }) })
    .selectOption('project_digest');
  await page.getByPlaceholder('Interval seconds').fill('3600');
  await page.getByRole('button', { name: /create schedule/i }).click();

  // The schedule appears in the schedules list.
  const scheduleRow = page.getByRole('listitem').filter({ hasText: scheduleName });
  await expect(scheduleRow).toBeVisible();
  await expect(scheduleRow).toContainText('project_digest');
  await expect(scheduleRow).toContainText('every 3600s');
  await expect(scheduleRow).toContainText('enabled');

  // Run it now -> a project_digest job lands in the Job history. The e2e stack
  // now runs a worker draining the queue (AOS-COUNCIL-PHASEC2B), so the job may
  // be queued/running/completed by the time it renders — assert presence by type
  // rather than a specific transient status.
  await scheduleRow.getByRole('button', { name: 'Run now' }).click();
  await expect(
    page.getByText(/project_digest — (queued|running|completed)/),
  ).toBeVisible({ timeout: 15000 });

  // Disable the schedule and confirm the row reflects it.
  await scheduleRow.getByRole('button', { name: 'Disable' }).click();
  await expect(scheduleRow).toContainText('disabled');
  await expect(scheduleRow.getByRole('button', { name: 'Enable' })).toBeVisible();

  // Reload persistence: the schedule and the job survive.
  await page.reload();
  await page.getByRole('button', { name: projectName }).first().click();
  await navTo(page, 'scheduling');
  await expect(page.getByRole('listitem').filter({ hasText: scheduleName })).toBeVisible();
  await expect(
    page.getByText(/project_digest — (queued|running|completed)/),
  ).toBeVisible({ timeout: 15000 });
});
