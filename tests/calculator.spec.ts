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
  await page.fill('#initialRoth', '200,000');
  await page.fill('#initialTrad', '1,500,000');
  await page.fill('#growthRate', '5');
  await page.fill('#marriedSS', '40,000');
  await page.fill('#singleSS', '25,000');
  await page.fill('#pension', '0');
  await page.fill('#withdrawalRate', '12');
  await page.fill('#fixedRothWD', '10,000');

  // Run simulation
  await page.click('button:has-text("Calculate Scenarios")');

  // Verify results container is visible
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });

  // Verify Comparison Summary
  await expect(page.locator('#taxA')).not.toHaveText('-');
  await expect(page.locator('#taxB')).not.toHaveText('-');
  await expect(page.locator('#conversionsA')).not.toHaveText('-');
  await expect(page.locator('#conversionsB')).not.toHaveText('-');
  await expect(page.locator('#balanceA')).not.toHaveText('-');
  await expect(page.locator('#balanceB')).not.toHaveText('-');

  // Verify Scenario B has conversions with default parameters while A might not
  const convBText = await page.locator('#conversionsB').innerText();
  const convBValue = parseFloat(convBText.replace(/[^0-9.-]+/g,""));
  expect(convBValue).toBeGreaterThan(0);

  // Switch to Charts tab
  await page.click('button:has-text("Charts")');
  const canvas = page.locator('#balanceChart');
  await expect(canvas).toBeVisible();

  // Switch to Details tab
  await page.click('button:has-text("Year-by-Year")');
  const rows = page.locator('#tableBody tr');
  await expect(rows).toHaveCount(31); // 95 - 65 + 1

  // Verify Roth Conv column is present and has data
  const rothConvVal = await page.locator('#tableBody tr:first-child td:nth-child(7)').innerText();
  expect(rothConvVal).toContain('$');
});

test('Form submits on Enter key', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');

  // Fill a field and press Enter
  await page.fill('#startAge', '60');
  await page.press('#startAge', 'Enter');

  // Verify results container is visible
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });

  // Verify age starts at 60 in the table
  await page.click('button:has-text("Year-by-Year")');
  const firstRowAge = await page.locator('#tableBody tr:first-child td:first-child').innerText();
  expect(firstRowAge).toBe('60');
});
