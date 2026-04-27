import { test, expect } from '@playwright/test';
import path from 'path';

test('Retirement calculator simulation runs and displays results', async ({ page }) => {
  const filePath = `file://${path.resolve('index.html')}`;
  await page.goto(filePath);

  // Check initial state
  await expect(page.locator('h1')).toHaveText('Retirement Calculator');

  // Fill the form (using default values but ensuring they are there)
  await page.fill('#start_age', '65');
  await page.fill('#end_age', '95');
  await page.fill('#spouse_death_age', '85');
  await page.fill('#roth_balance', '200000');
  await page.fill('#trad_balance', '500000');
  await page.fill('#ss_income', '40000');
  await page.fill('#growth_rate', '5');
  await page.fill('#withdrawal_rate', '4');

  // Run simulation
  await page.click('button[type="submit"]');

  // Verify results table is populated
  const rows = page.locator('#results-table tbody tr');
  await expect(rows).toHaveCount(31); // 95 - 65 + 1 = 31

  // Verify the first row data
  const firstRow = rows.first();
  await expect(firstRow.locator('td').nth(0)).toHaveText('65');
  await expect(firstRow.locator('td').nth(1)).toHaveText('married');

  // Verify filing status change
  const rowsAfterDeath = rows.nth(20); // Age 85 (65 + 20)
  await expect(rowsAfterDeath.locator('td').nth(0)).toHaveText('85');
  await expect(rowsAfterDeath.locator('td').nth(1)).toHaveText('single');

  // Verify chart canvas is present
  const canvas = page.locator('#balanceChart');
  await expect(canvas).toBeVisible();
});
