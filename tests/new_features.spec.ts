import { test, expect } from '@playwright/test';

test('QCD and Roth Conversion Toggle', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');

  // Set up a scenario where QCD should be visible
  await page.fill('#startAge', '70');
  await page.fill('#endAge', '75');
  await page.fill('#initialTrad', '1,000,000');
  await page.fill('#qcdPercentage', '10'); // 10% of 1M is 100k, below 108k limit

  // Disable Roth Conversions
  await page.uncheck('#enableConversion');

  await page.click('button:has-text("Calculate Scenarios")');

  // Verify results
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });

  // Total QCDs should be greater than 0
  const qcdAText = await page.locator('#qcdSumA').innerText();
  const qcdAValue = parseFloat(qcdAText.replace(/[^0-9.-]+/g,""));
  expect(qcdAValue).toBeGreaterThan(0);

  // Total Conversions should be 0 (or very close) since we disabled it
  const convAText = await page.locator('#conversionsA').innerText();
  const convAValue = parseFloat(convAText.replace(/[^0-9.-]+/g,""));
  expect(convAValue).toBeLessThan(1); // Should be exactly 0, but allow for small float diff

  // Check the table for QCD column
  await page.click('button:has-text("Year-by-Year")');
  const qcdCell = await page.locator('#tableBody tr:first-child td:nth-child(11)').innerText();
  expect(qcdCell).not.toBe('$0');
});
