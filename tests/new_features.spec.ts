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

test('RMD overrides Target if higher', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');

  // Set up scenario: RMD will be ~75k, but target is only 20k
  await page.fill('#startAge', '73');
  await page.fill('#endAge', '74');
  await page.fill('#initialTrad', '2,000,000');
  await page.fill('#initialRoth', '0');
  await page.fill('#withdrawalRate', '1'); // 1% of 2M = 20,000
  await page.uncheck('#enableConversion');

  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });

  await page.click('button:has-text("Year-by-Year")');

  // Age(1), Status(2), SS(3), Pension(4), Trad WD(5)
  const tradWD = await page.locator('#tableBody tr:first-child td:nth-child(5)').innerText();
  const tradWDVal = parseFloat(tradWD.replace(/[^0-9.-]+/g,""));

  // RMD = 2,000,000 / 26.5 = 75,471.70
  // Target = 20,000
  // tradWDVal should be around 75,472
  expect(tradWDVal).toBeGreaterThan(75000);
});
