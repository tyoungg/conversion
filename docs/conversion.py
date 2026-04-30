try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


# -----------------------------
# TAX FUNCTIONS
# -----------------------------
def calculate_tax(taxable_income, brackets):
    """Calculates tax on taxable income using progressive brackets."""
    tax = 0
    for lower, upper, rate in brackets:
        if taxable_income > lower:
            taxed_amount = min(taxable_income, upper) - lower
            tax += taxed_amount * rate
        else:
            break
    return tax


def calculate_taxable_ss(withdrawal_trad, other_taxable_income, ss_income, filing_status):
    """
    Simplified Social Security taxation based on provisional income.
    provisional_income = other_taxable_income + withdrawal_trad + 0.5 * ss_income
    """
    provisional_income = withdrawal_trad + other_taxable_income + 0.5 * ss_income

    if filing_status == "married":
        t1, t2 = 32000, 44000
    else:  # single
        t1, t2 = 25000, 34000

    if provisional_income < t1:
        taxable_ss = 0
    elif provisional_income < t2:
        taxable_ss = 0.5 * ss_income
    else:
        taxable_ss = 0.85 * ss_income

    return taxable_ss


# -----------------------------
# MEDICARE AND RMD FUNCTIONS
# -----------------------------
def calculate_medicare_premium(magi, filing_status, age):
    """Calculates annual Medicare premiums based on MAGI."""
    if age < 65:
        return 0

    if filing_status == "married":
        if magi <= 194000:
            monthly_premium = 164.90
        elif magi <= 246000:
            monthly_premium = 230.80
        elif magi <= 306000:
            monthly_premium = 321.80
        elif magi <= 366000:
            monthly_premium = 412.70
        else:
            monthly_premium = 503.70
    else:  # single
        if magi <= 97000:
            monthly_premium = 164.90
        elif magi <= 123000:
            monthly_premium = 230.80
        elif magi <= 153000:
            monthly_premium = 321.80
        elif magi <= 183000:
            monthly_premium = 412.70
        else:
            monthly_premium = 503.70

    return monthly_premium * 12


def calculate_rmd(account_balance, age, filing_status):
    """Calculates RMD based on prior year ending balance and IRS uniform lifetime table."""
    RMD_START_AGE = 73
    if age < RMD_START_AGE:
        return 0

    rmd_divisors = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
        78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5,
        83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4,
        88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8,
        93: 10.1, 94: 9.5, 95: 8.9, 96: 8.4, 97: 7.8,
        98: 7.3, 99: 6.8, 100: 6.4, 101: 6.0, 102: 5.6,
        103: 5.2, 104: 4.9, 105: 4.6, 106: 4.3, 107: 4.1,
        108: 3.9, 109: 3.7, 110: 3.5, 111: 3.4, 112: 3.3,
        113: 3.1, 114: 3.0, 115: 2.9, 116: 2.8, 117: 2.7,
        118: 2.5, 119: 2.3, 120: 2.0
    }
    divisor = rmd_divisors.get(age, 5.0 if age < 120 else 2.0)
    return account_balance / divisor


# -----------------------------
# SIMULATION ENGINE
# -----------------------------
def simulate_retirement(
    start_age,
    end_age,
    spouse_death_age,
    initial_roth_balance,
    initial_trad_balance,
    growth_rate,
    married_ss_income,
    single_ss_income,
    pension_income,
    withdrawal_rate,
    married_brackets=None,
    single_brackets=None,
    married_deduction=29200,
    single_deduction=14600,
    strategy="B",  # "A" = stop at 22%, "B" = stop at 24%
    include_rmd=True,
    include_medicare=True
):
    # Set defaults for brackets and deductions
    if married_brackets is None:
        married_brackets = [
            (0, 22000, 0.10),
            (22000, 89450, 0.12),
            (89450, 190750, 0.22),
            (190750, 364200, 0.24),
        ]

    if single_brackets is None:
        single_brackets = [
            (0, 11000, 0.10),
            (11000, 44725, 0.12),
            (44725, 95375, 0.22),
            (95375, 182100, 0.24),
        ]

    results = []
    roth_balance = initial_roth_balance
    trad_balance = initial_trad_balance
    prev_trad_balance = initial_trad_balance

    for age in range(start_age, end_age + 1):
        is_married = age < spouse_death_age
        filing_status = "married" if is_married else "single"
        brackets = married_brackets if is_married else single_brackets
        deduction = married_deduction if is_married else single_deduction
        ss_income = married_ss_income if is_married else single_ss_income

        if strategy == "A":
            tax_limit = brackets[2][1] if len(brackets) > 2 else 999999999
        else:
            tax_limit = brackets[3][1] if len(brackets) > 3 else 999999999

        rmd = calculate_rmd(prev_trad_balance, age, filing_status) if include_rmd else 0

        # Grow accounts at start of year
        roth_balance *= (1 + growth_rate)
        trad_balance *= (1 + growth_rate)

        # 1. Find optimized bracket limit for Traditional withdrawal
        low, high = 0, 2000000
        best_w_trad_limit = 0
        for _ in range(25):
            mid = (low + high) / 2
            t_ss = calculate_taxable_ss(mid, pension_income, ss_income, filing_status)
            t_inc = mid + pension_income + t_ss - deduction
            if t_inc <= tax_limit:
                best_w_trad_limit = mid
                low = mid
            else:
                high = mid

        # 2. Withdrawal & Conversion Strategy
        # Portfolio spending goal (Gross)
        portfolio_wd_goal = (trad_balance + roth_balance) * withdrawal_rate

        # Target Trad withdrawal for spending (at least RMD, but try to meet goal)
        trad_for_spending = min(max(rmd, portfolio_wd_goal), trad_balance)

        # Actual Trad: might take even more to fill the bracket (Optimization)
        actual_trad = min(max(trad_for_spending, best_w_trad_limit), trad_balance)

        actual_roth = 0
        if actual_trad < portfolio_wd_goal:
            # Trad was not enough to meet spending goal even after filling bracket
            actual_roth = min(portfolio_wd_goal - actual_trad, roth_balance)

        # Calculate Taxes & Medicare on total Trad withdrawal
        taxable_ss = calculate_taxable_ss(actual_trad, pension_income, ss_income, filing_status)
        taxable_income = max(0, actual_trad + pension_income + taxable_ss - deduction)
        total_taxes = calculate_tax(taxable_income, brackets)
        magi = actual_trad + pension_income + taxable_ss
        medicare = calculate_medicare_premium(magi, filing_status, age) if include_medicare else 0

        total_gross = actual_trad + actual_roth + ss_income + pension_income
        total_net = total_gross - (total_taxes + medicare)

        # Optimization: Convert surplus to Roth
        # Surplus is anything withdrawn beyond what was needed for spending goal (or RMD)
        if actual_trad > trad_for_spending:
            # Calculate taxes if we had only withdrawn for spending
            taxable_ss_no_conv = calculate_taxable_ss(trad_for_spending, pension_income, ss_income, filing_status)
            taxable_income_no_conv = max(0, trad_for_spending + pension_income + taxable_ss_no_conv - deduction)
            taxes_no_conv = calculate_tax(taxable_income_no_conv, brackets)

            # Net income if we only did spending
            net_spending = (trad_for_spending + actual_roth + ss_income + pension_income) - (taxes_no_conv + medicare)

            conversion_net = max(0, total_net - net_spending)
            roth_balance += conversion_net
            net_income = total_net - conversion_net
        else:
            net_income = total_net

        trad_balance -= actual_trad
        roth_balance -= actual_roth
        prev_trad_balance = trad_balance

        results.append({
            "Age": age,
            "Filing Status": filing_status,
            "Social Security": ss_income,
            "Pension": pension_income,
            "Traditional Withdrawal": actual_trad,
            "Roth Withdrawal": actual_roth,
            "Traditional Balance": trad_balance,
            "Roth Balance": roth_balance,
            "RMD Required": rmd,
            "Taxes": total_taxes,
            "Medicare Cost": medicare,
            "Net Income": net_income
        })

    return results


if __name__ == "__main__":
    test_params = {
        "start_age": 65,
        "end_age": 95,
        "spouse_death_age": 85,
        "initial_roth_balance": 200000,
        "initial_trad_balance": 1500000,
        "growth_rate": 0.05,
        "married_ss_income": 40000,
        "single_ss_income": 25000,
        "pension_income": 0,
        "withdrawal_rate": 0.12,
        "include_rmd": True,
        "include_medicare": True
    }

    results_a = simulate_retirement(**test_params, strategy="A")
    results_b = simulate_retirement(**test_params, strategy="B")

    def summarize(results):
        total_taxes = sum(r["Taxes"] for r in results)
        total_medicare = sum(r["Medicare Cost"] for r in results)
        total_expenses = total_taxes + total_medicare
        ending_balance = results[-1]["Roth Balance"] + results[-1]["Traditional Balance"]
        return total_taxes, total_medicare, total_expenses, ending_balance

    tax_a, medicare_a, expenses_a, bal_a = summarize(results_a)
    tax_b, medicare_b, expenses_b, bal_b = summarize(results_b)

    print("=" * 80)
    print("RETIREMENT STRATEGY COMPARISON")
    print("=" * 80)
    print(f"\nScenario A (Stop at 22%):")
    print(f"  Total Taxes:        ${tax_a:>15,.2f}")
    print(f"  Total Medicare:     ${medicare_a:>15,.2f}")
    print(f"  Total Expenses:     ${expenses_a:>15,.2f}")
    print(f"  Ending Balance:     ${bal_a:>15,.2f}")

    print(f"\nScenario B (Stop at 24%):")
    print(f"  Total Taxes:        ${tax_b:>15,.2f}")
    print(f"  Total Medicare:     ${medicare_b:>15,.2f}")
    print(f"  Total Expenses:     ${expenses_b:>15,.2f}")
    print(f"  Ending Balance:     ${bal_b:>15,.2f}")
    print("=" * 80)
