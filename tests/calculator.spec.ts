import { test, expect } from '@playwright/test';
import path from 'path';

test('Retirement calculator simulation runs and displays comparison results', async ({ page }) => {
  const filePath = `file://${path.resolve('docs/index.html')}`;
  await page.goto(filePath);

  // Check initial state
  await expect(page.locator('h1')).toHaveText('Retirement Calculator');

  // Fill the form
  await page.fill('#start_age', '65');
  await page.fill('#end_age', '95');
  await page.fill('#spouse_death_age', '85');
  await page.fill('#roth_balance', '200000');
  await page.fill('#trad_balance', '1500000');
  await page.fill('#ss_income', '40000');
  await page.fill('#growth_rate', '5');
  await page.fill('#withdrawal_rate', '6');

  // Verify new fields (now formatted with commas)
  await expect(page.locator('#married_deduction')).toHaveValue('29,200');
  await expect(page.locator('#married_ss_t1')).toHaveValue('32,000');

  // Run simulation
  await page.click('button[type="submit"]');

  // Verify results table is populated (Scenario A)
  const rows = page.locator('#results-table tbody tr');
  await expect(rows).toHaveCount(31);

  // Verify Comparison Summary
  await expect(page.locator('#tax-a')).not.toHaveText('$0');
  await expect(page.locator('#tax-b')).not.toHaveText('$0');
  await expect(page.locator('#bal-a')).not.toHaveText('$0');
  await expect(page.locator('#bal-b')).not.toHaveText('$0');

  // Verify chart canvas is present
  const canvas = page.locator('#balanceChart');
  await expect(canvas).toBeVisible();
});
