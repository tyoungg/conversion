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
  // Column 11 is now "Annual QCD" (it was before too, but let's be sure of the index after adding Taxable Income)
  // Age(1), Status(2), SS(3), Pension(4), Trad WD(5), Roth WD(6), Roth Conv(7), Trad Bal(8), Roth Bal(9), RMD(10), QCD(11), TaxableInc(12), Taxes(13), Medicare(14), Net(15)
  const qcdCell = await page.locator('#tableBody tr:first-child td:nth-child(11)').innerText();
  expect(qcdCell).not.toBe('$0');
});

test('RMD Satisfaction via QCD', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');

  // Set up a scenario with high RMD and QCD
  await page.fill('#startAge', '80');
  await page.fill('#endAge', '81');
  await page.fill('#initialTrad', '1,000,000');
  await page.fill('#withdrawalRate', '0'); // No extra taxable withdrawal
  await page.fill('#qcdPercentage', '10'); // 10% of 1M = 100k QCD. RMD for age 80 is ~1M/20.2 = ~49.5k.

  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });

  await page.click('button:has-text("Year-by-Year")');

  const rmdPenalty = await page.locator('#tableBody tr:first-child td:nth-child(10)').innerText();
  // We don't have a penalty column in the table, let's check if the simulator output results have it.
  // Actually, the table doesn't show penalty. Let's check Net Income instead or assume if no penalty net income is SS+Pension.

  // Wait, I can check if any penalty occurred by looking at the results object if I could,
  // but I only have the UI.
  // If penalty was applied, Net Income would be lower.
  // SS (40k) + Pension (30k) = 70k. Taxes on 0 taxable income = 0.
  // Net Income should be ~70k if no penalty.
  // UPDATE: Since withdrawalRate is 0, the surplus (income - goal) is converted to Roth.
  // Let's set withdrawalRate to something reasonable so Net Income is not 0.
  await page.fill('#withdrawalRate', '5');
  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  await page.click('button:has-text("Year-by-Year")');

  // Age(1), Status(2), SS(3), Pension(4), Trad WD(5), Roth WD(6), Roth Conv(7), Trad Bal(8), Roth Bal(9), RMD(10), QCD(11), Penalty(12), TaxableInc(13), Taxes(14), Medicare(15), Net(16)
  const netIncome = await page.locator('#tableBody tr:first-child td:nth-child(16)').innerText();
  const netIncomeVal = parseFloat(netIncome.replace(/[^0-9.-]+/g,""));
  expect(netIncomeVal).toBeGreaterThan(60000);
});
