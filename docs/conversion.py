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


def calculate_taxable_ss(withdrawal_trad, ss_income, filing_status):
    """
    Simplified Social Security taxation based on provisional income.
    provisional_income = non_ss_income + 0.5 * ss_income

    Note: Roth withdrawals do NOT count towards provisional income.
    Only Traditional/taxable withdrawals are included.
    """
    provisional_income = withdrawal_trad + 0.5 * ss_income

    # Standard thresholds (Simplified)
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
def calculate_medicare_premium(modified_adjusted_gross_income, filing_status, age):
    """
    Calculates Medicare Part B and D premiums based on MAGI (Modified Adjusted Gross Income).
    Uses 2024 IRMAA (Income-Related Monthly Adjustment Amount) brackets.

    Premiums increase with MAGI. This is simplified - uses standard brackets.
    Note: Actual premiums depend on state and specific plan.
    Note: Roth withdrawals do NOT count towards MAGI for Medicare IRMAA.
    Note: Pension income DOES count towards MAGI.
    """
    if age < 65:
        return 0  # No Medicare until 65

    # 2024 IRMAA brackets (simplified - combined Part B + Part D)
    # Returns monthly premium, multiply by 12 for annual
    if filing_status == "married":
        if modified_adjusted_gross_income <= 194000:
            monthly_premium = 164.90
        elif modified_adjusted_gross_income <= 246000:
            monthly_premium = 230.80
        elif modified_adjusted_gross_income <= 306000:
            monthly_premium = 321.80
        elif modified_adjusted_gross_income <= 366000:
            monthly_premium = 412.70
        else:
            monthly_premium = 503.70
    else:  # single
        if modified_adjusted_gross_income <= 97000:
            monthly_premium = 164.90
        elif modified_adjusted_gross_income <= 123000:
            monthly_premium = 230.80
        elif modified_adjusted_gross_income <= 153000:
            monthly_premium = 321.80
        elif modified_adjusted_gross_income <= 183000:
            monthly_premium = 412.70
        else:
            monthly_premium = 503.70

    return monthly_premium * 12  # Annual premium


def calculate_rmd(account_balance, age, filing_status):
    """
    Calculate Required Minimum Distribution (RMD) for Traditional IRA/401(k).
    RMD required starting at age 73 (as of 2023 SECURE Act 2.0).
    Uses IRS life expectancy tables (simplified with uniform divisor).

    Note: Roth IRA/401(k) do NOT have RMD requirements during account owner's lifetime.
    This function only applies to Traditional accounts.
    Note: Pension income does not have RMDs - it's a fixed payment stream.
    """
    RMD_START_AGE = 73

    if age < RMD_START_AGE:
        return 0

    # Simplified IRS life expectancy divisors (Uniform Lifetime Table)
    rmd_divisors = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
        78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5,
        83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4,
        88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8,
        93: 10.1, 94: 9.5, 95: 8.9, 96: 8.4, 97: 7.8,
        98: 7.3, 99: 6.8, 100: 6.4
    }

    divisor = rmd_divisors.get(age, 5.0)  # Default for ages beyond table
    rmd = account_balance / divisor

    return rmd


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

    for age in range(start_age, end_age + 1):
        # Filing status switch
        is_married = age < spouse_death_age
        filing_status = "married" if is_married else "single"
        brackets = married_brackets if is_married else single_brackets
        deduction = married_deduction if is_married else single_deduction

        # Social Security income changes when spouse passes
        ss_income = married_ss_income if is_married else single_ss_income

        # Target threshold for optimization
        if strategy == "A":
            # Upper bound of the 22% bracket (start of 24% bracket)
            tax_limit = brackets[2][1] if len(brackets) > 2 else 999999999
        else:
            # Strategy B: Upper bound of the 24% bracket (start of 32% bracket)
            tax_limit = brackets[3][1] if len(brackets) > 3 else 999999999

        # Grow accounts at start of year
        roth_balance *= (1 + growth_rate)
        trad_balance *= (1 + growth_rate)

        # Calculate Required Minimum Distribution (if applicable)
        rmd = 0
        if include_rmd:
            rmd = calculate_rmd(trad_balance, age, filing_status)

        # Determine target withdrawal (total needed from retirement accounts)
        target_withdrawal = max(trad_balance * withdrawal_rate, rmd)

        # Optimization logic: Find max W_trad such that taxable income <= tax_limit
        # AND total withdrawal >= target_withdrawal (filled by Roth)

        # Simple binary search for W_trad
        low = 0
        high = max(target_withdrawal, trad_balance) # Can withdraw more than target if RMD or high balance
        best_w_trad = 0

        for _ in range(20):
            mid = (low + high) / 2
            taxable_ss = calculate_taxable_ss(mid, ss_income, filing_status)
            taxable_income = max(0, mid + pension_income + taxable_ss - deduction)

            if taxable_income <= tax_limit:
                best_w_trad = mid
                low = mid
            else:
                high = mid

        # Actual withdrawal from Traditional is limited by balance and our "best" optimized amount
        # But must be at least the RMD if we have enough balance
        actual_withdrawal_trad = max(rmd, min(best_w_trad, trad_balance))
        # Wait, if RMD > best_w_trad, we HAVE to take RMD, pushing us over the limit.
        # min(best_w_trad, trad_balance) might be less than RMD if balance is low.
        actual_withdrawal_trad = min(actual_withdrawal_trad, trad_balance)

        trad_balance -= actual_withdrawal_trad

        # Remainder from Roth to reach target_withdrawal
        needed_from_roth = max(0, target_withdrawal - actual_withdrawal_trad)
        actual_withdrawal_roth = min(needed_from_roth, roth_balance)
        roth_balance -= actual_withdrawal_roth

        # Calculate taxes for the year
        taxable_ss = calculate_taxable_ss(actual_withdrawal_trad, ss_income, filing_status)
        taxable_income = max(0, actual_withdrawal_trad + pension_income + taxable_ss - deduction)
        taxes = calculate_tax(taxable_income, brackets)

        # Calculate Medicare costs
        medicare_cost = 0
        if include_medicare and age >= 65:
            magi = actual_withdrawal_trad + pension_income + ss_income
            medicare_cost = calculate_medicare_premium(magi, filing_status, age)

        # Total income includes all sources
        total_income = ss_income + pension_income + actual_withdrawal_trad + actual_withdrawal_roth
        total_expenses = taxes + medicare_cost
        net_income = total_income - total_expenses

        results.append({
            "Age": age,
            "Filing Status": filing_status,
            "Social Security": ss_income,
            "Pension": pension_income,
            "Traditional Withdrawal": actual_withdrawal_trad,
            "Roth Withdrawal": actual_withdrawal_roth,
            "Roth Balance": roth_balance,
            "Traditional Balance": trad_balance,
            "RMD Required": rmd,
            "Total Income": total_income,
            "Taxable Income": taxable_income,
            "Taxes": taxes,
            "Medicare Cost": medicare_cost,
            "Net Income": net_income
        })

    return results


# -----------------------------
# MAIN EXECUTION
# -----------------------------
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

    # Run simulations
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

    print(f"\nDifference (A vs B):")
    print(f"  Tax Difference:     ${tax_a - tax_b:>15,.2f} {'(A saves)' if tax_a < tax_b else '(B saves)'}")
    print(f"  Medicare Diff:      ${medicare_a - medicare_b:>15,.2f} {'(A saves)' if medicare_a < medicare_b else '(B saves)'}")
    print(f"  Total Expense Diff: ${expenses_a - expenses_b:>15,.2f} {'(A saves)' if expenses_a < expenses_b else '(B saves)'}")
    print(f"  Balance Difference: ${bal_a - bal_b:>15,.2f}")
    print("=" * 80)
