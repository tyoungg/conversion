import { test, expect } from '@playwright/test';

test('capture mobile table screenshot', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('http://localhost:8080/');

  // Click Calculate
  await page.click('button:has-text("Calculate Scenarios")');

  // Wait for results to be populated (the resultsContent becomes visible)
  await page.waitForSelector('#resultsContent:not(.results-hidden)', { timeout: 10000 });

  // Click Year-by-Year tab to make table visible
  await page.click('button:has-text("Year-by-Year")');

  // Wait for the table to be visible
  const table = page.locator('.data-table');
  await expect(table).toBeVisible();

  // Scroll to the table container
  const tableContainer = page.locator('.data-table-container').first();
  await tableContainer.scrollIntoViewIfNeeded();

  // Scroll the table to the right
  await tableContainer.evaluate(el => el.scrollLeft = 300);

  // Small delay for rendering
  await page.waitForTimeout(500);

  await page.screenshot({ path: 'verification/mobile_table_scrolled_v3.png' });

  const scrollLeft = await tableContainer.evaluate(el => el.scrollLeft);
  console.log(`Scroll Left: ${scrollLeft}`);
  expect(scrollLeft).toBeGreaterThan(0);
});
