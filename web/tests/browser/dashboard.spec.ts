import { test, expect } from '@playwright/test';

const british = '2024-british-gp-silverstone-race';
const japan = '2024-japanese-gp-suzuka-race';
const monza = '2023-italian-gp-monza-race';

async function ready(page) {
  await page.goto('/');
  await expect(page.locator('#matchup')).toContainText('ALB');
}

test('a driver cannot race their identical lap and ties have no winner', async ({ page }) => {
  await ready(page);
  await expect(page.locator('#driverB option[value="ALB"]')).toHaveJSProperty('disabled', true);
  await page.route('**/data/*.json', async route => {
    const response = await route.fetch();
    const body = await response.json();
    if (body.drivers) body.drivers.ALO.fastest.sec = body.drivers.ALB.fastest.sec;
    await route.fulfill({ response, json: body });
  });
  await page.reload();
  await expect(page.locator('#matchup')).toContainText('Equal lap time');
  await expect(page.locator('#matchup')).not.toContainText('faster');
});

test('tabs expose state, work with arrow keys, and survive a reload', async ({ page }) => {
  await ready(page);
  const pace = page.getByRole('tab', { name: 'Lap pace', exact: true });
  await expect(pace).toHaveAttribute('aria-selected', 'true');
  await pace.focus();
  await page.keyboard.press('ArrowRight');
  const telemetry = page.getByRole('tab', { name: 'Telemetry', exact: true });
  await expect(telemetry).toBeFocused();
  await expect(telemetry).toHaveAttribute('aria-selected', 'true');
  await expect(page).toHaveURL(/tab=telemetry/);
  await page.reload();
  await expect(telemetry).toHaveAttribute('aria-selected', 'true');
  await page.goBack();
  await expect(pace).toHaveAttribute('aria-selected', 'true');
});

test('charts remain within cards across resizing and tab revisits', async ({ page }) => {
  await ready(page);
  for (const width of [375, 1440, 760]) {
    await page.setViewportSize({ width, height: 900 });
    await page.getByRole('tab', { name: 'Telemetry', exact: true }).click();
    await page.getByRole('tab', { name: 'Lap pace', exact: true }).click();
    await expect.poll(() => page.locator('#chart-pace').evaluate(el => {
      const svg = el.querySelector('.main-svg');
      return !!svg && svg.getBoundingClientRect().bottom <= el.getBoundingClientRect().bottom;
    })).toBe(true);
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});

test('failed session changes preserve the comparison and offer retry', async ({ page }) => {
  await ready(page);
  await page.route(`**/data/${japan}.json`, route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await page.locator('#session').selectOption(japan);
  await expect(page.getByRole('alert')).toContainText('Could not load');
  await expect(page.locator('#session-sub')).toContainText('British');
  await expect(page).toHaveURL(new RegExp(british));
  await page.unroute(`**/data/${japan}.json`);
  await page.getByRole('button', { name: 'Retry' }).click();
  await expect(page.locator('#session-sub')).toContainText('Japanese');
});

test('late session responses cannot overwrite a newer selection', async ({ page }) => {
  await ready(page);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route(`**/data/${japan}.json`, async route => { await gate; await route.continue(); });
  await page.locator('#session').selectOption(japan);
  await page.locator('#session').selectOption(monza);
  await expect(page.locator('#session-sub')).toContainText('Italian');
  const response = page.waitForResponse(r => r.url().includes(japan));
  release();
  await response;
  await page.getByRole('tab', { name: 'Track & sectors' }).click();
  await expect(page.locator('#session-sub')).toContainText('Italian');
  await expect(page).toHaveURL(new RegExp(monza));
});

test('touch controls, readable tables, and chart reset are available', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await ready(page);
  for (const el of await page.locator('.tab, .controls select').all()) {
    expect((await el.boundingBox())!.height).toBeGreaterThanOrEqual(44);
  }
  await page.getByRole('tab', { name: 'Track & sectors' }).click();
  await expect(page.getByRole('table', { name: 'Sector comparison' })).toBeVisible();
  await page.getByRole('tab', { name: 'Lap pace', exact: true }).click();
  await page.getByText('View lap data', { exact: true }).click();
  await expect(page.getByRole('table', { name: 'Lap times' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reset chart zoom' })).toBeVisible();
  await page.getByRole('tab', { name: 'Tyres & weather', exact: true }).click();
  await page.getByText('View stint data', { exact: true }).click();
  await expect(page.getByRole('table', { name: 'Tyre stints' })).toContainText('INTERMEDIATE');
});

test('initial failures can be retried without reloading the page', async ({ page }) => {
  await page.route('**/data/index.json', route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('Could not load the session list');
  await expect(page.locator('#driverA')).toBeDisabled();
  await page.unroute('**/data/index.json');
  await page.getByRole('button', { name: 'Retry' }).click();
  await expect(page.locator('#matchup')).toContainText('ALB');
  await expect(page.getByRole('alert')).toBeHidden();
});

test('a session without a model never retains previous model results', async ({ page }) => {
  await ready(page);
  await page.getByRole('tab', { name: 'Pace model', exact: true }).click();
  await expect(page.getByRole('table', { name: 'Degradation evidence' })).toBeVisible();
  await page.route(`**/data/${japan}.json`, async route => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...await response.json(), model: null } });
  });
  await page.locator('#session').selectOption(japan);
  await expect(page.locator('#model-metrics')).toContainText('Not enough green laps');
  await expect(page.locator('#chart-degradation')).toBeHidden();
  await expect(page.locator('#degradation-data')).toBeEmpty();
  await page.locator('#session').selectOption(british);
  await expect(page.locator('#chart-degradation .main-svg').first()).toBeVisible();
});

test('unavailable telemetry has a recoverable view-level message', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', err => errors.push(err.message));
  await page.route(`**/data/${british}.json`, async route => {
    const response = await route.fetch();
    const data = await response.json();
    data.drivers.ALB.telemetry = [];
    await route.fulfill({ response, json: data });
  });
  await ready(page);
  await page.getByRole('tab', { name: 'Telemetry', exact: true }).click();
  await expect(page.locator('#panel-telemetry')).toContainText('Telemetry needs at least two samples');
  await expect(page).toHaveURL(/tab=telemetry/);
  await page.locator('#driverA').selectOption('VER');
  await expect(page.locator('#chart-speed .main-svg').first()).toBeVisible();
  expect(errors).toEqual([]);
});

test('reset zoom restores the full lap range after a drag zoom', async ({ page }) => {
  await ready(page);
  const plot = page.locator('#chart-pace .chart-canvas');
  await expect.poll(() => plot.evaluate((el: any) => !!el._fullLayout)).toBe(true);
  const original = await plot.evaluate((el: any) => el._fullLayout.xaxis.range);
  const drag = await page.locator('#chart-pace .nsewdrag').boundingBox();
  await page.mouse.move(drag!.x + drag!.width * .2, drag!.y + drag!.height * .2);
  await page.mouse.down();
  await page.mouse.move(drag!.x + drag!.width * .7, drag!.y + drag!.height * .8, { steps: 6 });
  await page.mouse.up();
  await expect.poll(() => plot.evaluate((el: any) => el._fullLayout.xaxis.autorange)).toBe(false);
  await page.getByRole('button', { name: 'Reset chart zoom' }).click();
  await expect.poll(() => plot.evaluate((el: any) => el._fullLayout.xaxis.range)).toEqual(original);
});
