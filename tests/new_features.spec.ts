import { test, expect } from '@playwright/test';

test('QCD and Roth Conversion Toggle', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.fill('#startAge', '70');
  await page.fill('#endAge', '75');
  await page.fill('#initialTrad', '1,000,000');
  await page.fill('#qcdPercentage', '10');
  await page.uncheck('#enableConversion');
  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  const qcdAText = await page.locator('#qcdSumA').innerText();
  expect(parseFloat(qcdAText.replace(/[^0-9.-]+/g,""))).toBeGreaterThan(0);
});

test('RMD Satisfaction via QCD', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.fill('#startAge', '80');
  await page.fill('#initialTrad', '1,000,000');
  await page.fill('#withdrawalRate', '5');
  await page.fill('#qcdPercentage', '10');
  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  await page.click('button:has-text("Year-by-Year")');
  const netIncome = await page.locator('#tableBody tr:first-child td:nth-child(16)').innerText();
  expect(parseFloat(netIncome.replace(/[^0-9.-]+/g,""))).toBeGreaterThan(60000);
});

test('RMD overrides Target if higher', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.fill('#startAge', '73');
  await page.fill('#initialTrad', '2,000,000');
  await page.fill('#initialRoth', '0');
  await page.fill('#withdrawalRate', '1');
  await page.uncheck('#enableConversion');
  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  await page.click('button:has-text("Year-by-Year")');
  const tradWD = await page.locator('#tableBody tr:first-child td:nth-child(5)').innerText();
  expect(parseFloat(tradWD.replace(/[^0-9.-]+/g,""))).toBeGreaterThan(75000);
});

test('High Balance (200M) handling', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.fill('#initialTrad', '200,000,000');
  await page.fill('#withdrawalRate', '5');
  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 30000 });
  await page.click('button:has-text("Year-by-Year")');
  const outflow = await page.locator('#tableBody tr:first-child td:nth-child(17)').innerText();
  expect(parseFloat(outflow.replace(/[^0-9.-]+/g,""))).toBeGreaterThan(9999000);
});

test('RMD overflow bracket - Zero Conversions', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.fill('#startAge', '85');
  await page.fill('#spouseDeathAge', '80');
  await page.fill('#initialTrad', '4,000,000');
  await page.fill('#initialRoth', '0');
  await page.fill('#withdrawalRate', '1');
  await page.check('#enableConversion');
  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  const convAText = await page.locator('#conversionsA').innerText();
  expect(parseFloat(convAText.replace(/[^0-9.-]+/g,""))).toBeLessThan(1);
});
