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
    if ss_income <= 0:
        return 0

    provisional = withdrawal_trad + other_income + 0.5 * ss_income

    if filing_status == "married":
        t1, t2 = 32000, 44000
        max_50_pct_tier = 6000  # (44000 - 32000) * 0.5
    else:
        t1, t2 = 25000, 34000
        max_50_pct_tier = 4500  # (34000 - 25000) * 0.5

    if provisional <= t1:
        return 0

    # Amount in the 50% tier (between T1 and T2)
    tier1_amt = min(provisional, t2) - t1
    taxable_50 = 0.5 * tier1_amt

    # Amount in the 85% tier (above T2)
    tier2_amt = max(0, provisional - t2)
    taxable_85 = 0.85 * tier2_amt

    # Tiered amount logic:
    # 1. Start with 85% of excess over T2
    # 2. Add the smallest of:
    #    a) The 50% tier amount calculated above
    #    b) 50% of the SS benefit
    #    c) The max allowance for tier 1 ($6000 for married, $4500 for single)
    combined_tiered = taxable_85 + min(taxable_50, 0.5 * ss_income, max_50_pct_tier)

    # Total taxable is the smaller of the tiered result or 85% of total SS.
    return min(combined_tiered, 0.85 * ss_income)


# -----------------------------
# MEDICARE + RMD
# -----------------------------
def calculate_medicare_premium(magi, filing_status, age):
    """
    Calculates annual Medicare Part B premiums including IRMAA based on 2025 rates.
    Doubles the premium for married couples (assuming both are 65+).
    """
    if age < 65:
        return 0

    # 2025 IRMAA Thresholds (MAGI from 2 years prior, but using 2025 brackets for simulation)
    if filing_status == "married":
        brackets = [212000, 266000, 334000, 400000, 750000]
    else:
        brackets = [106000, 133000, 167000, 200000, 500000]

    # 2025 Monthly Premiums (Part B)
    # $185.00 standard, then IRMAA tiers
    premiums = [185.00, 259.00, 370.00, 480.90, 591.90, 628.90]

    selected_premium = premiums[-1]
    for i, limit in enumerate(brackets):
        # For the final bracket ($500k/$750k), the top tier starts at "greater than or equal to".
        # All lower tiers use "up to" (inclusive).
        is_last_bracket = (i == len(brackets) - 1)
        if (magi < limit if is_last_bracket else magi <= limit):
            selected_premium = premiums[i]
            break

    annual_premium = selected_premium * 12
    return annual_premium * 2 if filing_status == "married" else annual_premium


def calculate_rmd(balance, age, rmd_start_age=73):
    """
    Calculates Required Minimum Distribution.
    Note: Roth IRAs are not subject to RMDs for the original owner.
    """
    if age < rmd_start_age or balance <= 0:
        return 0

    # IRS Uniform Lifetime Table (Simplified/Standard)
    divisors = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
        78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5,
        83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4,
        88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8,
        93: 10.1, 94: 9.5, 95: 8.9, 96: 8.4, 97: 7.8,
        98: 7.3, 99: 6.8, 100: 6.4
    }

    divisor = divisors.get(age, divisors[max(divisors.keys())] if age > 100 else 10)
    return balance / divisor


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
    strategy="B",
    include_rmd=True,
    include_medicare=True,
    fixed_roth_withdrawal=0,
    enable_roth_conversion=True,
    qcd_percentage=0
):
    # 2025 Tax Brackets (Full 7-tier)
    married_brackets = [
        (0, 23850, 0.10),
        (23850, 96950, 0.12),
        (96950, 206700, 0.22),
        (206700, 394600, 0.24),
        (394600, 501050, 0.32),
        (501050, 751600, 0.35),
        (751600, float('inf'), 0.37)
    ]

    single_brackets = [
        (0, 11925, 0.10),
        (11925, 48475, 0.12),
        (48475, 103350, 0.22),
        (103350, 197300, 0.24),
        (197300, 250525, 0.32),
        (250525, 626350, 0.35),
        (626350, float('inf'), 0.37)
    ]

    results = []
    roth = initial_roth_balance
    trad = initial_trad_balance
    prev_trad = initial_trad_balance

    # Gross Withdrawal Target (Total amount to pull from accounts before taxes)
    gross_withdrawal_target = (initial_trad_balance + initial_roth_balance) * withdrawal_rate

    # SECURE 2.0 RMD Age Logic
    birth_year = 2025 - start_age
    rmd_start_age = 75 if birth_year >= 1960 else 73

    for age in range(start_age, end_age + 1):
        # IRS rule: You can file Married Filing Jointly for the year your spouse dies.
        married = age <= spouse_death_age
        status = "married" if married else "single"
        ss = married_ss_income if married else single_ss_income

        brackets = married_brackets if married else single_brackets

        # 2025 Standard Deduction + Age 65+ Additional Deduction
        if married:
            # Married: $30,000 + $1,600 * 2 (assuming both 65+)
            deduction = 30000 + (3200 if age >= 65 else 0)
        else:
            # Single: $15,000 + $2,000 (if 65+)
            deduction = 15000 + (2000 if age >= 65 else 0)

        # Strategy A (22%) or B (24%)
        bracket_limit = brackets[2][1] if strategy == "A" else brackets[3][1]

        # Grow Accounts
        roth *= (1 + growth_rate)
        trad *= (1 + growth_rate)

        # 1. QCD
        qcd_amount = 0
        if age >= 70:
            # 2025 limit: $108,000 per individual
            qcd_limit = 216000 if status == "married" else 108000
            # QCD is taken first from the Gross Withdrawal Target
            qcd_amount = min(trad, qcd_limit, trad * qcd_percentage, gross_withdrawal_target)
            trad -= qcd_amount

        # 2. RMD (Mandatory)
        rmd = calculate_rmd(prev_trad, age, rmd_start_age) if include_rmd else 0
        # QCD satisfies RMD dollar-for-dollar
        rmd_taxable_requirement = max(0, rmd - qcd_amount)
        rmd_taken = min(rmd_taxable_requirement, trad)
        trad -= rmd_taken

        # 3. Optimized Traditional Withdrawal
        # Remaining gross target after QCD and RMD
        remaining_gross_target = max(0, gross_withdrawal_target - qcd_amount - rmd_taken)

        # Binary search for extra Traditional withdrawal
        low, high = 0, trad
        best_extra = 0
        for _ in range(20):
            mid = (low + high) / 2
            test_trad = rmd_taken + mid
            t_ss = calculate_taxable_ss(test_trad, pension_income, ss, status)
            t_income = max(0, test_trad + pension_income + t_ss - deduction)

            if enable_roth_conversion:
                if t_income <= bracket_limit:
                    best_extra = mid
                    low = mid
                else:
                    high = mid
            else:
                # Without conversions, only withdraw up to the remaining gross target
                if mid <= remaining_gross_target and t_income <= bracket_limit:
                    best_extra = mid
                    low = mid
                else:
                    high = mid

        extra_trad = best_extra
        trad -= extra_trad
        total_trad = rmd_taken + extra_trad

        # 4. Calculate Taxes and Medicare
        taxable_ss = calculate_taxable_ss(total_trad, pension_income, ss, status)
        taxable_income = max(0, total_trad + pension_income + taxable_ss - deduction)
        taxes = calculate_tax(taxable_income, brackets)

        magi = total_trad + pension_income + taxable_ss
        medicare = calculate_medicare_premium(magi, status, age) if include_medicare else 0

        # 5. Roth Withdrawal to meet remaining gross target
        gross_so_far = qcd_amount + total_trad
        remaining_target_for_roth = max(0, gross_withdrawal_target - gross_so_far)

        roth_withdrawal = min(roth, fixed_roth_withdrawal + remaining_target_for_roth)
        roth -= roth_withdrawal

        # 6. Determine Net Income and Conversion
        net_income = (total_trad + ss + pension_income + roth_withdrawal) - (taxes + medicare)

        roth_conversion = 0
        if enable_roth_conversion:
            # Baseline is what we would have withdrawn if only meeting gross target
            baseline_trad = max(rmd_taken, min(total_trad, max(0, gross_withdrawal_target - qcd_amount)))
            baseline_ss = calculate_taxable_ss(baseline_trad, pension_income, ss, status)
            baseline_taxable = max(0, baseline_trad + pension_income + baseline_ss - deduction)
            baseline_taxes = calculate_tax(baseline_taxable, brackets)
            baseline_magi = baseline_trad + pension_income + baseline_ss
            baseline_medicare = calculate_medicare_premium(baseline_magi, status, age) if include_medicare else 0

            baseline_net = (baseline_trad + ss + pension_income + roth_withdrawal) - (baseline_taxes + baseline_medicare)

            if net_income > baseline_net:
                roth_conversion = net_income - baseline_net
                roth += roth_conversion
                net_income = baseline_net

        # 7. RMD Penalty
        shortfall_rmd = max(0, rmd - (total_trad + qcd_amount))
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
            "QCD Amount": qcd_amount,
            "Traditional Balance": trad,
            "Roth Balance": roth,
            "RMD Required": rmd,
            "RMD Penalty": penalty,
            "Taxable Income": taxable_income,
            "Taxes": taxes,
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
        "withdrawal_rate": 0.12
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
