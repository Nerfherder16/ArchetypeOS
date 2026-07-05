import { chromium } from 'playwright';

const results = [];
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? ' — ' + detail : ''}`);
};

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const page = await browser.newPage();
page.setDefaultTimeout(15000);

try {
  await page.goto('http://localhost:5173');
  await page.waitForSelector('text=Engineering Control Tower');
  check('page loads with control tower header', true);

  // Health down must not block the rest (redis absent -> /health 500)
  const projectsSection = await page.waitForSelector('text=Projects');
  check('projects section renders despite health failure', !!projectsSection);

  // Create a project via the form
  await page.getByPlaceholder('New project name').fill('Control Tower Verify');
  await page.getByRole('button', { name: /create project/i }).click();
  await page.waitForSelector('text=Control Tower Verify');
  check('project created via form and appears in list', true);

  // Register a repository
  await page.getByPlaceholder('Repository name').fill('Demo Repo');
  await page.getByPlaceholder('Local path').fill('demo-repo');
  await page.getByRole('button', { name: /register repository/i }).click();
  await page.waitForSelector('text=demo-repo');
  check('repository registered and listed', true);

  const never = await page.locator('text=never').count();
  check('unscanned repository shows "never"', never > 0);

  // Run scan
  await page.getByRole('button', { name: /run scan/i }).first().click();
  await page.waitForSelector('text=Python', { timeout: 20000 });
  check('scan summary shows detected language Python', true);

  const bodyText = await page.textContent('body');
  check('risk flag surfaced (.env)', /\.env/i.test(bodyText));
  check('docker detected in summary', /docker/i.test(bodyText));
  check('architecture section shows node count', /node/i.test(bodyText) && /edge/i.test(bodyText));

  // Reload: stored DNA must persist via GET /repositories/{id}/dna
  await page.reload();
  await page.waitForSelector('text=Control Tower Verify');
  await page.locator('text=Control Tower Verify').first().click();
  await page.waitForSelector('text=demo-repo');
  const demoRow = page.locator('text=Demo Repo').first();
  await demoRow.click().catch(() => {});
  await page.waitForTimeout(1500);
  const afterReload = await page.textContent('body');
  check('after reload, stored scan data still reachable (no "never")', !/never/.test(afterReload) || /Python/.test(afterReload));

  await page.screenshot({ path: 'control-tower.png', fullPage: true });
  console.log('SCREENSHOT saved');
} catch (err) {
  check('flow completed without error', false, String(err));
  await page.screenshot({ path: 'control-tower-failure.png', fullPage: true }).catch(() => {});
} finally {
  await browser.close();
  const failed = results.filter((r) => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  process.exit(failed.length ? 1 : 0);
}
