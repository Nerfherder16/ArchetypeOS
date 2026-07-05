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

  await page.getByPlaceholder('New project name').fill('Digest Verify');
  await page.getByRole('button', { name: /create project/i }).click();
  await page.waitForSelector('text=Digest Verify');

  // Register + scan a repo without tests so the missing-tests draft rule fires
  await page.getByPlaceholder('Repository name').fill('No Tests Repo');
  await page.getByPlaceholder('Local path').fill('demo-repo');
  await page.getByRole('button', { name: /register repository/i }).click();
  await page.waitForSelector('text=demo-repo');
  await page.getByRole('button', { name: /run scan/i }).first().click();
  await page.waitForSelector('text=Python', { timeout: 20000 });
  check('setup: repo scanned', true);

  await page.waitForSelector('text=Nightly Digest');
  check('Nightly Digest section renders', true);

  await page.getByRole('button', { name: /run digest/i }).click();
  await page.waitForSelector('text=scan runs', { timeout: 15000 });
  const body = await page.textContent('body');
  check('digest listed with summary counts', /1 repositories/.test(body) && /scan runs/.test(body));
  check('draft recommendation visible (Add tests)', /Add tests to/i.test(body));

  // Placeholder removed
  check('"Nightly digest view" placeholder removed', !/Nightly digest view/.test(body));
  check('voice inbox placeholder retained', /Voice inbox/i.test(body));

  // Reload persistence
  await page.reload();
  await page.waitForSelector('text=Digest Verify');
  await page.locator('text=Digest Verify').first().click();
  await page.waitForSelector('text=scan runs');
  check('digest persists across reload', true);

  await page.screenshot({ path: 'nightly-digest.png', fullPage: true });
  console.log('SCREENSHOT saved');
} catch (err) {
  check('flow completed without error', false, String(err));
  await page.screenshot({ path: 'digest-failure.png', fullPage: true }).catch(() => {});
} finally {
  await browser.close();
  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  process.exit(failed.length ? 1 : 0);
}
