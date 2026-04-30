# Retirement Tax Conversion Strategy Simulator

A Python and Web-based tool to simulate and compare different retirement withdrawal strategies, focusing on tax-efficient conversions between Traditional IRA and Roth accounts.

## Overview

This project helps retirees optimize their withdrawal strategy by comparing two approaches:
- **Strategy A**: Conservative approach that stops withdrawals at the 22% tax bracket threshold
- **Strategy B**: Aggressive approach that goes into the 24% tax bracket

The simulator models year-by-year retirement scenarios with realistic tax calculations including Social Security income taxation and Medicare Part B premiums (IRMAA).

## Features

- 📊 **Progressive Tax Calculation**: Uses actual federal tax brackets (2024).
- 🔄 **Social Security Taxation**: Models provisional income-based taxation (0%, 50%, or 85%).
- 🏥 **Medicare IRMAA**: Calculates Medicare Part B premiums based on income tiers.
- 👫 **Marital Status Changes**: Handles spouse mortality and filing status transitions.
- 📈 **Account Growth**: Models portfolio growth during retirement.
- 📋 **Detailed Results**: Year-by-year breakdown of balances, withdrawals, taxes, and net income.
- 📈 **Interactive Visualization**: Web-based charts using Chart.js.

## Installation & Setup

### For Web UI (Recommended)
The tool is designed to run in a web browser using Pyodide (Python in the browser).

1. Clone the repository:
   ```bash
   git clone https://github.com/tyoungg/conversion.git
   cd conversion
   ```
2. Start a local web server:
   ```bash
   python3 -m http.server 8080 --directory docs
   ```
3. Open your browser to `http://localhost:8080`

### For Command Line
1. Navigate to the `docs` directory:
   ```bash
   cd docs
   ```
2. Run the simulation:
   ```bash
   python3 conversion.py
   ```

## Usage

### Web Interface
Fill in your retirement details in the left panel:
- **Starting/Ending Age**: Your planned retirement horizon.
- **Initial Balances**: Current amounts in Traditional and Roth accounts.
- **Income Sources**: Social Security (Married/Single) and any Pension.
- **Withdrawal Rate**: Target percentage of your portfolio to withdraw annually.

Click **"Calculate Scenarios"** to see a side-by-side comparison and detailed year-by-year breakdowns.

### CLI (Advanced)
Edit the default parameters in the `if __name__ == "__main__":` block of `docs/conversion.py` to customize your run.

## Key Concepts

### Progressive Tax Brackets
The simulator uses 2024 federal tax brackets, applying income progressively from lowest to highest brackets.

### Withdrawal Strategies

**Strategy A (Conservative)**
- Maximizes withdrawals while staying within the 22% bracket.
- Uses binary search to find the optimal Traditional withdrawal amount.
- Remaining need filled from Roth.

**Strategy B (Aggressive)**
- Maximizes withdrawals up to the 24% bracket.
- Generally results in faster Traditional account depletion but higher initial taxes.

## File Structure

```
conversion/
├── docs/
│   ├── conversion.py       # Main simulation logic (Python)
│   └── index.html         # Web UI (HTML/JS/Pyodide)
├── tests/
│   └── calculator.spec.ts # Playwright E2E tests
├── README.md              # This file
├── package.json           # Test dependencies
└── retirement_ui_v2.png   # UI mockup
```

## Testing

End-to-end tests are written with Playwright.
```bash
npm install
npx playwright test
```

## Disclaimer

This tool provides simplified tax calculations for educational/planning purposes only. Actual tax liability depends on individual circumstances, state taxes, and other factors not modeled here. **Consult a qualified tax professional before making withdrawal decisions.**
