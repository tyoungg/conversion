# Retirement Tax Conversion Strategy Simulator

A Python tool to simulate and compare different retirement withdrawal strategies, focusing on tax-efficient conversions between Traditional IRA and Roth accounts.

## Overview

This project helps retirees optimize their withdrawal strategy by comparing two approaches:
- **Strategy A**: Conservative approach that stops withdrawals at the 22% tax bracket threshold
- **Strategy B**: Aggressive approach that goes into the 24% tax bracket

The simulator models year-by-year retirement scenarios with realistic tax calculations including Social Security income taxation.

## Features

- 📊 **Progressive Tax Calculation**: Uses actual federal tax brackets
- 🔄 **Social Security Taxation**: Simplified provisional income-based taxation model
- 👫 **Marital Status Changes**: Handles spouse mortality and filing status transitions
- 📈 **Account Growth**: Models portfolio growth during accumulation phases
- 📉 **Withdrawal Strategies**: Compares multiple withdrawal approaches
- 📋 **Detailed Results**: Year-by-year breakdown of balances, withdrawals, and taxes
- 📈 **Visualization**: Optional plotting with matplotlib to compare scenarios

## Installation

### Requirements
- Python 3.7+
- pandas (optional, for dataframe output)
- matplotlib (optional, for visualizations)

### Setup

```bash
# Clone the repository
git clone https://github.com/tyoungg/conversion.git
cd conversion

# Install optional dependencies (recommended)
pip install pandas matplotlib
```

## Usage

Run the simulator with default parameters:

```bash
python conversion.py
```

### Customizing Parameters

Edit the `params` dictionary in `conversion.py` to adjust:

```python
params = {
    "start_age": 65,                    # Starting retirement age
    "end_age": 95,                      # Projected end age
    "spouse_death_age": 85,             # Age when spouse passes (affects filing status)
    "initial_roth_balance": 200000,     # Starting Roth IRA balance
    "initial_trad_balance": 1500000,    # Starting Traditional IRA balance
    "growth_rate": 0.05,                # Annual growth rate (5%)
    "ss_income": 40000,                 # Annual Social Security income
    "withdrawal_rate": 0.12,            # Annual withdrawal rate from Traditional
    "married_brackets": [...],          # Married filing jointly tax brackets
    "single_brackets": [...],           # Single filer tax brackets
    "married_deduction": 29200,         # Standard deduction (married)
    "single_deduction": 14600           # Standard deduction (single)
}
```

## Output

The simulator produces:
- **Console summary**: Total taxes paid and ending balance for each strategy
- **DataFrame head**: First rows of detailed year-by-year results (requires pandas)
- **Visualization**: Chart comparing account balances over time (requires matplotlib)

Example output:
```
Scenario A (Stop at 22%): Total Taxes = $456,234.50, Ending Balance = $2,134,567.89
Scenario B (Go into 24%): Total Taxes = $512,345.67, Ending Balance = $2,089,123.45
```

## Key Concepts

### Progressive Tax Brackets
The simulator uses the actual 2024 federal tax brackets, applying income progressively from lowest to highest brackets.

### Social Security Taxation
Uses the provisional income formula:
```
Provisional Income = Non-SS Income + 0.5 × Social Security Income
```

Based on provisional income thresholds, up to 85% of Social Security can be taxable.

### Withdrawal Strategies

**Strategy A (Conservative)**
- Maximizes withdrawals while staying within the 22% bracket
- Uses binary search to find optimal Traditional withdrawal amount
- Remaining need filled from Roth
- Ideal for those wanting to minimize tax bracket increases

**Strategy B (Aggressive)**
- Withdraws from Traditional first up to target amount
- Then uses Roth as needed
- Simplest to execute
- May push into higher brackets

## File Structure

```
conversion/
├── conversion.py           # Main simulation engine
├── README.md              # This file
├── package.json           # Node/Playwright configuration (legacy)
├── retirement_ui_v2.png   # UI mockup (related project)
├── docs/                  # Documentation (empty)
├── tests/                 # Unit tests (empty)
└── test-results/          # Test results (empty)
```

## Contributing

Contributions welcome! Areas for improvement:
- Add unit tests in `tests/`
- Extend to handle more complex tax scenarios (AMT, NII tax, etc.)
- Add state income tax modeling
- Create interactive UI for parameter input
- Add data export to CSV/Excel

## TODO

- [ ] Add comprehensive unit tests
- [ ] Implement state income tax calculations
- [ ] Create web UI (Playwright tests suggest this is planned)
- [ ] Add more bracket years/historical data
- [ ] Implement Required Minimum Distribution (RMD) rules
- [ ] Add Roth conversion modeling
- [ ] Performance benchmarking for different strategies

## License

Not specified - add LICENSE file

## Author

Created by @tyoungg

## Disclaimer

This tool provides simplified tax calculations for educational/planning purposes only. Actual tax liability depends on individual circumstances, state taxes, and other factors not modeled here. **Consult a qualified tax professional before making withdrawal decisions.**
