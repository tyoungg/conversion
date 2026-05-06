import { test, expect } from '@playwright/test';

test('Dynamic Social Security Claiming Age', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.waitForSelector("#loadingMessage", { state: "hidden", timeout: 30000 });

  // Accept disclaimer
  await page.click('#closeDisclaimer');

  await page.selectOption('#filingStatus', 'single');
  await page.fill('#ssPrimaryFRA', '3,000');
  await page.fill('#birthYearPrimary', '1960');
  await page.fill('#claimAgePrimary', '62');
  await page.fill('#startAge', '60');
  await page.fill('#endAge', '65');
  await page.uncheck('#enableConversion');

  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  await page.click('button:has-text("Year-by-Year")');

  const ss62 = await page.locator('#tableBody tr:nth-child(3) td:nth-child(3)').innerText();
  expect(ss62).toBe('$25,200');
});

test('Spousal Benefit Higher than Own', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.waitForSelector("#loadingMessage", { state: "hidden", timeout: 30000 });

  // Accept disclaimer
  await page.click('#closeDisclaimer');

  await page.fill('#ssPrimaryFRA', '3,000');
  await page.fill('#claimAgePrimary', '67');
  await page.fill('#ssSpouseFRA', '500');
  await page.fill('#birthYearSpouse', '1960');
  await page.fill('#claimAgeSpouse', '67');
  await page.fill('#startAge', '67');
  await page.fill('#endAge', '68');

  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  await page.click('button:has-text("Year-by-Year")');

  const totalSS = await page.locator('#tableBody tr:nth-child(1) td:nth-child(3)').innerText();
  expect(totalSS).toBe('$54,000');
});

test('Drain Traditional First logic', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.waitForSelector("#loadingMessage", { state: "hidden", timeout: 30000 });

  // Accept disclaimer
  await page.click('#closeDisclaimer');

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

test('Robustness to legacy arguments', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.waitForSelector("#loadingMessage", { state: "hidden", timeout: 30000 });

  // Accept disclaimer
  await page.click('#closeDisclaimer');

  const result = await page.evaluate(async () => {
    // @ts-ignore
    const response = await fetch('./conversion.py');
    const pythonCode = await response.text();
    // @ts-ignore
    const py = window.wrappedPyodide || window.pyodide;

    const params = {
      start_age: 65, end_age: 70, spouse_death_age: 85,
      initial_roth_balance: 100000, initial_trad_balance: 100000,
      growth_rate: 0.05, pension_income: 0, withdrawal_rate: 0.04,
      fixed_roth_withdrawal: 0, qcd_percentage: 0,
      enable_roth_conversion: false, filing_status: 'single',
      ss_primary_fra: 2000, birth_year_primary: 1960, claim_age_primary: 67,
      married_ss_income: 40000
    };

    const simCode = `
import json
params = json.loads('${JSON.stringify(params)}')
${pythonCode}
simulate_retirement(**params)
`;
    try {
      await py.runPythonAsync(simCode);
      return "SUCCESS";
    } catch (e) {
      return e.message;
    }
  });

  expect(result).toBe("SUCCESS");
});

test('Optional Roth Buffer Toggle', async ({ page }) => {
  await page.goto('http://localhost:8080/index.html');
  await page.waitForSelector("#loadingMessage", { state: "hidden", timeout: 30000 });

  // Accept disclaimer
  await page.click('#closeDisclaimer');

  // 1M Trad, 1M Roth. 5% = 100k target.
  await page.fill('#initialTrad', '1,000,000');
  await page.fill('#initialRoth', '1,000,000');
  await page.fill('#withdrawalRate', '5');
  await page.uncheck('#enableConversion');

  // Case 1: Buffer ENABLED (Default)
  await page.check('#useRothBuffer');
  await page.click('button:has-text("Calculate Scenarios")');
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  await page.click('button:has-text("Year-by-Year")');

  // Withdrawal should be ~100k
  const outflowEnabled = await page.locator('#tableBody tr:first-child td:nth-child(18)').innerText();
  expect(parseFloat(outflowEnabled.replace(/[^0-9.-]+/g,""))).toBeCloseTo(100000, -2);

  // Case 2: Buffer DISABLED
  // We need a scenario where Trad alone doesn't meet target.
  // Set Trad to 20k, Target 100k.
  await page.fill('#initialTrad', '20,000');
  await page.uncheck('#useRothBuffer');
  await page.click('button:has-text("Calculate Scenarios")');

  // Wait for the table to update
  await expect(page.locator('#resultsContent')).toBeVisible({ timeout: 20000 });
  await page.click('button:has-text("Year-by-Year")');

  const outflowDisabled = await page.locator('#tableBody tr:first-child td:nth-child(18)').innerText();
  // Should be ~20k (only Trad)
  expect(parseFloat(outflowDisabled.replace(/[^0-9.-]+/g,""))).toBeLessThan(30000);
});
