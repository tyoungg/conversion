import { test, expect } from '@playwright/test';

test('Retirement calculator simulation runs and displays comparison results', async ({ page }) => {
  // Use http server to avoid CORS issues with fetch
  await page.goto('http://localhost:8080/index.html');

  // Check initial state
  await expect(page.locator('h1')).toHaveText('💰 Retirement Tax Conversion Strategy Simulator');

  // Fill the form
  await page.fill('#startAge', '65');
  await page.fill('#endAge', '95');
  await page.fill('#spouseDeathAge', '85');
  await page.fill('#initialRoth', '200000');
  await page.fill('#initialTrad', '1500000');
  await page.fill('#growthRate', '5');
  await page.fill('#marriedSS', '40000');
  await page.fill('#singleSS', '25000');
  await page.fill('#pension', '0');
  await page.fill('#withdrawalRate', '12');

  // Run simulation
  await page.click('button:has-text("Calculate Scenarios")');

  // Verify results container is visible
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });

  // Verify Comparison Summary
  await expect(page.locator('#taxA')).not.toHaveText('-');
  await expect(page.locator('#taxB')).not.toHaveText('-');
  await expect(page.locator('#balanceA')).not.toHaveText('-');
  await expect(page.locator('#balanceB')).not.toHaveText('-');

  // Switch to Charts tab
  await page.click('button:has-text("Charts")');
  const canvas = page.locator('#balanceChart');
  await expect(canvas).toBeVisible();

  // Switch to Details tab
  await page.click('button:has-text("Year-by-Year")');
  const rows = page.locator('#tableBody tr');
  await expect(rows).toHaveCount(31); // 95 - 65 + 1
});
