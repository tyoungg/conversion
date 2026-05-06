import { test, expect } from '@playwright/test';

test('Verify MAGI column and Scenario B toggle', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.waitForSelector("#loadingMessage", { state: "hidden", timeout: 30000 });

  // Accept disclaimer
  await page.click('#closeDisclaimer');

  await page.fill('#initialTrad', '1,000,000');
  await page.fill('#initialRoth', '1,000,000');
  await page.fill('#withdrawalRate', '5');

  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  await page.click('button:has-text("Year-by-Year")');

  // Verify headers
  const headers = await page.locator('#dataTable thead th').allInnerTexts();
  expect(headers).toContain('MAGI');
  const magiIdx = headers.indexOf('MAGI') + 1;

  // Verify Scenario A is shown by default
  const title = await page.locator('#detailsTitle').innerText();
  expect(title).toContain('Scenario A');

  // Check some values in the table
  const magiValA = await page.locator(`#tableBody tr:first-child td:nth-child(${magiIdx})`).innerText();
  expect(magiValA).not.toBe('');

  // Switch to Scenario B
  await page.click('#btnShowB');
  const titleB = await page.locator('#detailsTitle').innerText();
  expect(titleB).toContain('Scenario B');

  const magiValB = await page.locator(`#tableBody tr:first-child td:nth-child(${magiIdx})`).innerText();
  expect(magiValB).not.toBe('');
});
