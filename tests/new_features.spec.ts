import { test, expect } from '@playwright/test';

test('Dynamic Social Security Claiming Age', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.waitForSelector("#loadingMessage", { state: "hidden", timeout: 30000 });

  // Set filing status to Single
  await page.selectOption('#filingStatus', 'single');

  // Person 1: $3000 at FRA(67), Claim at 62
  await page.fill('#ssPrimaryFRA', '3,000');
  await page.fill('#birthYearPrimary', '1960');
  await page.fill('#claimAgePrimary', '62');

  await page.fill('#startAge', '60');
  await page.fill('#endAge', '65');
  await page.uncheck('#enableConversion');

  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  await page.click('button:has-text("Year-by-Year")');

  // At age 60, 61 SS should be 0
  const ss60 = await page.locator('#tableBody tr:nth-child(1) td:nth-child(3)').innerText();
  const ss61 = await page.locator('#tableBody tr:nth-child(2) td:nth-child(3)').innerText();
  expect(ss60).toBe('$0');
  expect(ss61).toBe('$0');

  // At age 62, SS should start.
  // $3000 reduced for 60 months (30%). $3000 * 0.7 = $2100 monthly = $25,200 annual
  const ss62 = await page.locator('#tableBody tr:nth-child(3) td:nth-child(3)').innerText();
  expect(ss62).toBe('$25,200');
});

test('Spousal Benefit Higher than Own', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.waitForSelector("#loadingMessage", { state: "hidden", timeout: 30000 });

  // Married
  await page.fill('#ssPrimaryFRA', '3,000'); // 3k
  await page.fill('#claimAgePrimary', '67');

  await page.fill('#ssSpouseFRA', '500'); // Spouse own is very low
  await page.fill('#birthYearSpouse', '1960');
  await page.fill('#claimAgeSpouse', '67'); // Claim at FRA

  await page.fill('#startAge', '67');
  await page.fill('#endAge', '68');

  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  await page.click('button:has-text("Year-by-Year")');

  // Combined SS: Primary(36k) + Spouse(18k because 50% of 3k is 1.5k monthly) = 54k
  const totalSS = await page.locator('#tableBody tr:nth-child(1) td:nth-child(3)').innerText();
  expect(totalSS).toBe('$54,000');
});

test('Drain Traditional First logic', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.waitForSelector("#loadingMessage", { state: "hidden", timeout: 30000 });

  await page.fill('#initialTrad', '1,000,000');
  await page.fill('#initialRoth', '1,000,000');
  await page.fill('#withdrawalRate', '5');
  await page.uncheck('#enableConversion');

  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  await page.click('button:has-text("Year-by-Year")');

  const tradWD = await page.locator('#tableBody tr:first-child td:nth-child(5)').innerText();
  const rothWD = await page.locator('#tableBody tr:first-child td:nth-child(6)').innerText();

  expect(parseFloat(tradWD.replace(/[^0-9.-]+/g,""))).toBeGreaterThan(99000);
  expect(parseFloat(rothWD.replace(/[^0-9.-]+/g,""))).toBe(0);
});
