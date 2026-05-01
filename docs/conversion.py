# -----------------------------
# TAX FUNCTIONS
# -----------------------------
def calculate_tax(taxable_income, brackets):
    tax = 0
    for lower, upper, rate in brackets:
        if taxable_income > lower:
            taxed_amount = min(taxable_income, upper) - lower
            tax += taxed_amount * rate
        else:
            break
    return tax


def calculate_taxable_ss(withdrawal_trad, other_income, ss_income, filing_status):
    """
    Calculates the taxable portion of Social Security benefits based on IRS
    provisional income thresholds.
    """
    provisional = withdrawal_trad + other_income + 0.5 * ss_income

    if filing_status == "married":
        t1, t2 = 32000, 44000
        max_50_pct_tier = 6000  # (44000 - 32000) * 0.5
    else:
        t1, t2 = 25000, 34000
        max_50_pct_tier = 4500  # (34000 - 25000) * 0.5

    if provisional <= t1:
        return 0

    # Amount in the 50% tier
    tier1_amt = min(provisional, t2) - t1
    taxable_50 = 0.5 * tier1_amt

    # Amount in the 85% tier
    tier2_amt = max(0, provisional - t2)
    taxable_85 = 0.85 * tier2_amt

    # The actual taxable amount is the lesser of the calculated tiered amount or 85% of SS.
    # The tiered amount is (85% of amount over T2) + (lesser of 50% tier amount, 50% of SS, or the max tier 1 allowance)
    combined_tiered = taxable_85 + min(taxable_50, 0.5 * ss_income, max_50_pct_tier)

    return min(combined_tiered, 0.85 * ss_income)


# -----------------------------
# MEDICARE + RMD
# -----------------------------
def calculate_medicare_premium(magi, filing_status, age):
    if age < 65:
        return 0

    if filing_status == "married":
        brackets = [194000, 246000, 306000, 366000]
    else:
        brackets = [97000, 123000, 153000, 183000]

    premiums = [164.90, 230.80, 321.80, 412.70, 503.70]

    for i, limit in enumerate(brackets):
        if magi <= limit:
            return premiums[i] * 12

    return premiums[-1] * 12


def calculate_rmd(balance, age):
    if age < 73 or balance <= 0:
        return 0

    divisors = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
        78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5,
        83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4,
        88: 13.7, 89: 12.9, 90: 12.2
    }

    divisor = divisors.get(age, 10)
    return balance / divisor


# -----------------------------
# SIMULATION ENGINE (FIXED)
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
    strategy="B",
    include_rmd=True,
    include_medicare=True,
    fixed_roth_withdrawal=0
):
    # 2024 Tax Brackets
    married_brackets = [
        (0, 23200, 0.10),
        (23200, 94300, 0.12),
        (94300, 201050, 0.22),
        (201050, 383900, 0.24),
    ]

    single_brackets = [
        (0, 11600, 0.10),
        (11600, 47150, 0.12),
        (47150, 100525, 0.22),
        (100525, 191950, 0.24),
    ]

    results = []
    roth = initial_roth_balance
    trad = initial_trad_balance
    prev_trad = initial_trad_balance

    # Stable Spending Target (Net)
    # Note: We derive this from the initial balances and withdrawal rate
    # This remains the annual goal for the entire simulation
    annual_spending_goal = (initial_trad_balance + initial_roth_balance) * withdrawal_rate

    for age in range(start_age, end_age + 1):
        married = age < spouse_death_age
        status = "married" if married else "single"
        ss = married_ss_income if married else single_ss_income

        brackets = married_brackets if married else single_brackets
        deduction = 29200 if married else 14600

        # Strategy A (22%) or B (24%)
        bracket_limit = brackets[2][1] if strategy == "A" else brackets[3][1]

        # Grow Accounts
        roth *= (1 + growth_rate)
        trad *= (1 + growth_rate)

        # 1. RMD (Mandatory)
        rmd = calculate_rmd(prev_trad, age) if include_rmd else 0
        rmd_taken = min(rmd, trad)
        trad -= rmd_taken

        # 2. Optimized Traditional Withdrawal (Targeting Bracket Limit)
        # We want to see how much we can withdraw from Trad without exceeding bracket_limit
        low, high = 0, trad
        best_extra = 0
        for _ in range(20):
            mid = (low + high) / 2
            test_trad = rmd_taken + mid
            t_ss = calculate_taxable_ss(test_trad, pension_income, ss, status)
            t_income = max(0, test_trad + pension_income + t_ss - deduction)
            if t_income <= bracket_limit:
                best_extra = mid
                low = mid
            else:
                high = mid

        extra_trad = best_extra
        trad -= extra_trad
        total_trad = rmd_taken + extra_trad

        # 3. Calculate Taxes and Medicare on this Optimized Trad Amount
        taxable_ss = calculate_taxable_ss(total_trad, pension_income, ss, status)
        taxable_income = max(0, total_trad + pension_income + taxable_ss - deduction)
        taxes = calculate_tax(taxable_income, brackets)

        magi = total_trad + pension_income + taxable_ss
        medicare = calculate_medicare_premium(magi, status, age) if include_medicare else 0

        # 4. Determine Net Available vs Spending Goal
        # Net from Trad + SS + Pension
        net_available = (total_trad + ss + pension_income) - (taxes + medicare)

        roth_conversion = 0

        # User specified fixed Roth withdrawal
        roth_withdrawal = min(fixed_roth_withdrawal, roth)
        roth -= roth_withdrawal

        # Current net including fixed Roth withdrawal
        current_net = net_available + roth_withdrawal

        if current_net > annual_spending_goal:
            # We have excess! This is the "Conversion" part.
            # We move the excess net income into the Roth IRA.
            roth_conversion = current_net - annual_spending_goal
            roth += roth_conversion
            net_income = annual_spending_goal
        else:
            # We have a shortfall. Use Roth to bridge it if possible.
            shortfall = annual_spending_goal - current_net
            additional_roth_wd = min(shortfall, roth)
            roth -= additional_roth_wd
            roth_withdrawal += additional_roth_wd

            net_income = current_net + additional_roth_wd

            # If still short and Roth is empty, we must take more from Trad (ignoring brackets)
            final_shortfall = annual_spending_goal - net_income
            if final_shortfall > 0 and trad > 0:
                # This is a bit of a recursive problem because taking more Trad increases taxes.
                # Simplified: take enough Trad to cover shortfall + estimated tax (roughly 25-30%)
                emergency_trad = min(trad, final_shortfall / 0.7)
                trad -= emergency_trad
                total_trad += emergency_trad

                # Recalculate taxes/medicare with emergency withdrawal
                taxable_ss = calculate_taxable_ss(total_trad, pension_income, ss, status)
                taxable_income = max(0, total_trad + pension_income + taxable_ss - deduction)
                taxes = calculate_tax(taxable_income, brackets)
                magi = total_trad + pension_income + taxable_ss
                medicare = calculate_medicare_premium(magi, status, age) if include_medicare else 0

                net_income = (total_trad + ss + pension_income + roth_withdrawal) - (taxes + medicare)

        # 5. RMD Penalty
        shortfall_rmd = max(0, rmd - total_trad)
        penalty = shortfall_rmd * 0.25
        net_income -= penalty

        prev_trad = trad

        results.append({
            "Age": age,
            "Filing Status": status,
            "Social Security": ss,
            "Pension": pension_income,
            "Traditional Withdrawal": total_trad,
            "Roth Withdrawal": roth_withdrawal,
            "Roth Conversion": roth_conversion,
            "Traditional Balance": trad,
            "Roth Balance": roth,
            "RMD Required": rmd,
            "RMD Penalty": penalty,
            "Taxes": taxes,
            "Medicare Cost": medicare,
            "Net Income": net_income
        })

    return results


if __name__ == "__main__":
    # Default test parameters
    test_params = {
        "start_age": 65,
        "end_age": 91,
        "spouse_death_age": 79,
        "initial_roth_balance": 2000000,
        "initial_trad_balance": 1500000,
        "growth_rate": 0.05,
        "married_ss_income": 40000,
        "single_ss_income": 25000,
        "pension_income": 30000,
        "withdrawal_rate": 0.05
    }

    print("Running Retirement Simulation...")
    print("-" * 40)

    for strat in ["A", "B"]:
        results = simulate_retirement(**test_params, strategy=strat)
        total_tax = sum(r["Taxes"] for r in results)
        total_medicare = sum(r["Medicare Cost"] for r in results)
        total_conversions = sum(r["Roth Conversion"] for r in results)
        ending_bal = results[-1]["Roth Balance"] + results[-1]["Traditional Balance"]

        strategy_name = "Stop at 22%" if strat == "A" else "Stop at 24%"
        print(f"Scenario {strat} ({strategy_name}):")
        print(f"  Total Taxes:       ${total_tax:,.2f}")
        print(f"  Total Medicare:    ${total_medicare:,.2f}")
        print(f"  Total Conversions: ${total_conversions:,.2f}")
        print(f"  Ending Balance:    ${ending_bal:,.2f}")
        print("-" * 40)
