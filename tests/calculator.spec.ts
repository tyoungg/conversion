import { test, expect } from '@playwright/test';

test('Retirement calculator simulation runs and displays comparison results', async ({ page }) => {
  // Use http server to avoid CORS issues with fetch
  await page.goto('http://localhost:8080/index.html');
  await page.waitForSelector("#loadingMessage", { state: "hidden", timeout: 30000 });

  // Fill out the form
  await page.fill('#startAge', '65');
  await page.fill('#endAge', '91');
  await page.fill('#spouseDeathAge', '79');
  await page.fill('#initialRoth', '1,500,000');
  await page.fill('#initialTrad', '2,000,000');
  await page.fill('#growthRate', '5.5');

  // New SS Inputs
  await page.fill('#ssPrimaryFRA', '2,500');
  await page.fill('#ssSpouseFRA', '1,000');

  await page.fill('#pension', '30,000');
  await page.fill('#withdrawalRate', '5');

  await page.click('button:has-text("Calculate Scenarios")');

  // Verify results container is visible
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });

  // Verify Comparison Summary
  await expect(page.locator('#taxA')).not.toHaveText('-');
  await expect(page.locator('#medicareA')).not.toHaveText('-');
  await expect(page.locator('#balanceA')).not.toHaveText('-');

  // Switch to Charts tab to verify chart
  await page.click('button:has-text("Charts")');
  await expect(page.locator('.chart-container')).toBeVisible();

  // Verify Year-by-Year table has data
  await page.click('button:has-text("Year-by-Year")');
  const rowCount = await page.locator('#tableBody tr').count();
  expect(rowCount).toBeGreaterThan(20);

  // Check specific column values (Age 65)
  const firstAge = await page.locator('#tableBody tr:first-child td:first-child').innerText();
  expect(firstAge).toBe('65');
});

test('Form submits on Enter key', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.waitForSelector("#loadingMessage", { state: "hidden", timeout: 30000 });

  // Focus an input and press Enter
  await page.focus('#startAge');
  await page.fill('#startAge', '60');
  await page.press('#startAge', 'Enter');

  // Verify results container is visible
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });

  // Verify age starts at 60 in the table
  await page.click('button:has-text("Year-by-Year")');
  const firstAge = await page.locator('#tableBody tr:first-child td:first-child').innerText();
  expect(firstAge).toBe('60');
});
