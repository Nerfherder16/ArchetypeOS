import { chromium } from 'playwright';

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok });
  console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? ' — ' + detail : ''}`);
};

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const page = await browser.newPage();
page.setDefaultTimeout(15000);

try {
  await page.goto('http://localhost:5173');
  await page.waitForSelector('text=Engineering Control Tower');

  await page.getByPlaceholder('New project name').fill('Decisions Verify');
  await page.getByRole('button', { name: /create project/i }).click();
  await page.waitForSelector('text=Decisions Verify');
  check('project created and selected', true);

  await page.waitForSelector('text=Decisions & Research');
  check('Decisions & Research section renders for selected project', true);

  // Create a research note
  await page.getByPlaceholder('Research note title').fill('Postgres vs SQLite tradeoffs');
  await page.getByPlaceholder('Summary').fill('Postgres for runtime, SQLite for tests.');
  await page.getByRole('button', { name: /add research note/i }).click();
  await page.waitForSelector('text=Postgres vs SQLite tradeoffs');
  check('research note created via form and listed', true);

  // Create a decision linked to the note via the select
  await page.getByPlaceholder('Decision title').fill('Keep dual-database posture');
  await page.getByPlaceholder('Decision text').fill('Postgres in compose, SQLite in tests, per research.');
  const select = page.locator('select').last();
  await select.selectOption({ index: 1 });
  await page.getByRole('button', { name: /add decision/i }).click();
  await page.waitForSelector('text=Keep dual-database posture');
  check('decision created via form and listed', true);

  const body1 = await page.textContent('body');
  check('linked research count visible on decision', /1/.test(body1) && body1.includes('Keep dual-database posture'));

  // Reload persistence
  await page.reload();
  await page.waitForSelector('text=Decisions Verify');
  await page.locator('text=Decisions Verify').first().click();
  await page.waitForSelector('text=Keep dual-database posture');
  await page.waitForSelector('text=Postgres vs SQLite tradeoffs');
  check('artifacts persist across reload', true);

  // API-level confirmation of the typed evidence link
  const api = await page.evaluate(async () => {
    const projects = await (await fetch('http://localhost:8000/projects')).json();
    const decisions = await (await fetch(`http://localhost:8000/projects/${projects[0].id}/decisions`)).json();
    return decisions[0]?.evidence ?? [];
  });
  check('decision evidence contains typed research_note entry', api.some((e) => e && e.type === 'research_note' && e.id));

  await page.screenshot({ path: 'decisions-research.png', fullPage: true });
  console.log('SCREENSHOT saved');
} catch (err) {
  check('flow completed without error', false, String(err));
  await page.screenshot({ path: 'decisions-failure.png', fullPage: true }).catch(() => {});
} finally {
  await browser.close();
  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  process.exit(failed.length ? 1 : 0);
}
