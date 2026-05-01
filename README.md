# 💰 Retirement Tax Conversion Strategy Simulator (2025 Edition)

A high-fidelity retirement withdrawal and tax optimization engine. This tool helps retirees compare different withdrawal strategies to minimize lifetime taxes, maximize ending balances, and understand the impact of the "Widow's Penalty."

## 🚀 Key Features

- **Stable Net Spending Goal:** The simulation derives an annual spending target based on your initial portfolio and a configurable withdrawal rate. It maintains this net income level throughout retirement.
- **Roth Conversion Ladder:**
    - **Scenario A:** Optimized to fill the **22%** federal tax bracket.
    - **Scenario B:** Optimized to fill the **24%** federal tax bracket.
    - *Logic:* The engine maximizes Traditional IRA withdrawals up to the target bracket. Any net income generated beyond the spending goal is automatically converted to the Roth IRA.
- **Precise 2025 Tax Engine:**
    - Uses full 7-tier federal tax brackets (Updated for 2025).
    - Includes the **IRS tiered Social Security taxation formula** (0%, 50%, and 85% tiers).
    - Automatically applies **Additional Standard Deductions** for taxpayers age 65 and older ($2,000 for Single, $1,600 per person for Married).
    - Models the **"Widow's Penalty"**: Transitioning from Married to Single filing status (brackets, deductions, and SS benefits) when a spouse passes.
- **Medicare IRMAA Modeling:**
    - Calculates **2025** Medicare Part B premiums ($185.00 base).
    - Factors in IRMAA surcharges based on MAGI (using 2025 tiers).
    - Correctly doubles premiums for married couples.
- **Account Buffering:**
    - Fulfills RMDs first (Traditional IRA/401k only).
    - **Note:** Roth IRAs are correctly modeled as having **zero RMDs**.
    - Uses Roth assets as a buffer if Traditional withdrawals (within optimized brackets) don't meet the spending goal.
    - Automated "Emergency" Traditional withdrawals if Roth assets are exhausted.

## 🛠 Usage

1.  **Enter Your Data:** Provide starting ages, portfolio balances, and income sources (Social Security, Pensions).
2.  **Set Goals:** Define your withdrawal rate and optional fixed Roth withdrawals.
3.  **Calculate:** The engine runs two parallel simulations (Scenario A and Scenario B).
4.  **Analyze:**
    - **Summary:** Compare total lifetime taxes, Medicare costs, and ending balances.
    - **Charts:** Visualize account balance depletion and annual Roth conversion amounts.
    - **Details:** Inspect year-by-year breakdowns of every tax and withdrawal event.

## 🧪 Technical Details

- **Frontend:** Single Page Application (SPA) using HTML/CSS/JS.
- **Simulation Engine:** Written in Python and executed in the browser via **Pyodide**.
- **Visualizations:** Powered by **Chart.js**.
- **Withdrawal Priority:**
    1.  Required Minimum Distributions (RMDs) from Traditional accounts.
    2.  Fixed Roth Withdrawals (if configured).
    3.  Optimized Traditional Withdrawals (filling brackets).
    4.  Roth Buffer (to reach spending goal).
    5.  Excess Traditional (if goal still not met).

## 📊 2025 Tax Assumptions

- **Standard Deduction (65+):**
    - Married: $34,700 ($31,500 + $3,200)
    - Single: $17,750 ($15,750 + $2,000)
- **Medicare Part B (Base):** $185.00/month per person.
- **Social Security:** Taxable portion calculated using Provisional Income thresholds ($25k/$34k for Single, $32k/$44k for Married).

## 🚩 Local Development

Because the application fetches `conversion.py` dynamically, you must serve it via a local web server to avoid CORS/file-protocol errors:

```bash
# Using Python
python3 -m http.server 8000 --directory docs

# Then open http://localhost:8000
```
