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
    combined_tiered = taxable_85 + min(taxable_50, 0.5 * ss_income, max_50_pct_tier)

    # Total taxable is the smaller of the tiered result or 85% of total SS.
    return min(combined_tiered, 0.85 * ss_income)


# -----------------------------
# MEDICARE + RMD
# -----------------------------
def calculate_medicare_premium(magi, filing_status, age):
    """
    Calculates annual Medicare Part B premiums including IRMAA based on 2025 rates.
    """
    if age < 65:
        return 0

    if filing_status == "married":
        brackets = [212000, 266000, 334000, 400000, 750000]
    else:
        brackets = [106000, 133000, 167000, 200000, 500000]

    premiums = [185.00, 259.00, 370.00, 480.90, 591.90, 628.90]

    selected_premium = premiums[-1]
    for i, limit in enumerate(brackets):
        is_last_bracket = (i == len(brackets) - 1)
        if (magi < limit if is_last_bracket else magi <= limit):
            selected_premium = premiums[i]
            break

    annual_premium = selected_premium * 12
    return annual_premium * 2 if filing_status == "married" else annual_premium


def calculate_rmd(balance, age, rmd_start_age=73):
    """
    Calculates Required Minimum Distribution.
    """
    if age < rmd_start_age or balance <= 0:
        return 0

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
    # 2025 Tax Brackets
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
    # Calculated once based on initial portfolio to maintain a stable spending goal.
    gross_withdrawal_target = (initial_trad_balance + initial_roth_balance) * withdrawal_rate

    # SECURE 2.0 RMD Age Logic
    birth_year = 2025 - start_age
    rmd_start_age = 75 if birth_year >= 1960 else 73

    for age in range(start_age, end_age + 1):
        married = age <= spouse_death_age
        status = "married" if married else "single"
        ss = married_ss_income if married else single_ss_income
        brackets = married_brackets if married else single_brackets

        if married:
            deduction = 30000 + (3200 if age >= 65 else 0)
        else:
            deduction = 15000 + (2000 if age >= 65 else 0)

        bracket_limit = brackets[2][1] if strategy == "A" else brackets[3][1]

        # Grow Accounts
        roth *= (1 + growth_rate)
        trad *= (1 + growth_rate)

        # 1. QCD
        qcd_amount = 0
        if age >= 70:
            qcd_limit = 216000 if status == "married" else 108000
            # QCD is taken from the Traditional balance based on user percentage.
            # It satisfies RMD requirements and reduces the taxable portion of withdrawals.
            qcd_amount = min(trad, qcd_limit, trad * qcd_percentage)
            trad -= qcd_amount

        # 2. RMD
        rmd = calculate_rmd(prev_trad, age, rmd_start_age) if include_rmd else 0
        rmd_taxable_requirement = max(0, rmd - qcd_amount)
        rmd_taken = min(trad, rmd_taxable_requirement)
        trad -= rmd_taken

        def get_tax_data(test_trad_total):
            t_ss = calculate_taxable_ss(test_trad_total, pension_income, ss, status)
            t_inc = max(0, test_trad_total + pension_income + t_ss - deduction)
            t_tax = calculate_tax(t_inc, brackets)
            t_magi = test_trad_total + pension_income + t_ss
            t_med = calculate_medicare_premium(t_magi, status, age) if include_medicare else 0
            return t_inc, t_tax, t_med

        # 3. Optimized Withdrawal
        remaining_target = max(0, gross_withdrawal_target - qcd_amount - rmd_taken)

        low, high = 0, trad
        best_extra = 0
        for _ in range(40):
            mid = (low + high) / 2
            t_inc, _, _ = get_tax_data(rmd_taken + mid)
            if enable_roth_conversion:
                if t_inc <= bracket_limit - 1:
                    best_extra = mid
                    low = mid
                else:
                    high = mid
            else:
                if mid <= remaining_target and t_inc <= bracket_limit:
                    best_extra = mid
                    low = mid
                else:
                    high = mid

        extra_trad = best_extra
        trad -= extra_trad
        current_trad_wd = rmd_taken + extra_trad

        # 4. Roth Withdrawal
        remaining_target = max(0, gross_withdrawal_target - qcd_amount - current_trad_wd)
        roth_wd = min(roth, fixed_roth_withdrawal + remaining_target)
        roth -= roth_wd

        # 5. Emergency Trad
        remaining_target = max(0, gross_withdrawal_target - qcd_amount - current_trad_wd - roth_wd)
        if remaining_target > 0 and trad > 0:
            emergency = min(trad, remaining_target)
            trad -= emergency
            current_trad_wd += emergency

        # 6. Taxes & Penalty
        taxable_income, taxes, medicare = get_tax_data(current_trad_wd)
        shortfall = max(0, rmd - (current_trad_wd + qcd_amount))
        penalty = shortfall * 0.25

        net_income = (current_trad_wd + ss + pension_income + roth_wd) - (taxes + medicare + penalty)

        # 7. Conversion
        roth_conv = 0
        if enable_roth_conversion:
            # Baseline is what we would have withdrawn if only meeting gross target
            baseline_trad_extra = min(extra_trad, remaining_gross_target)
            baseline_trad = rmd_taken + baseline_trad_extra
            baseline_ss = calculate_taxable_ss(baseline_trad, pension_income, ss, status)
            baseline_taxable = max(0, baseline_trad + pension_income + baseline_ss - deduction)
            baseline_taxes = calculate_tax(baseline_taxable, brackets)
            baseline_magi = baseline_trad + pension_income + baseline_ss
            baseline_medicare = calculate_medicare_premium(baseline_magi, status, age) if include_medicare else 0

            # Baseline penalty check
            baseline_shortfall = max(0, rmd - (baseline_trad + qcd_amount))
            baseline_penalty = baseline_shortfall * 0.25
            baseline_net = (baseline_trad + ss + pension_income + roth_withdrawal) - (baseline_taxes + baseline_medicare + baseline_penalty)

            if net_income > baseline_net:
                roth_conversion = net_income - baseline_net
                roth += roth_conversion
                net_income -= roth_conversion

        prev_trad = trad

        results.append({
            "Age": age,
            "Filing Status": status,
            "Social Security": ss,
            "Pension": pension_income,
            "Taxable Trad W/D": current_trad_wd,
            "Roth Withdrawal": roth_wd,
            "Roth Conversion": roth_conv,
            "QCD Amount": qcd_amount,
            "Traditional Balance": trad,
            "Roth Balance": roth,
            "RMD Required": rmd,
            "RMD Penalty": penalty,
            "Taxable Income": taxable_income,
            "Taxes": taxes,
            "Medicare Cost": medicare,
            "Net Income": net_income,
            "Total Outflow": current_trad_wd + roth_wd + qcd_amount
        })

    return results


if __name__ == "__main__":
    test_params = {
        "start_age": 65, "end_age": 95, "spouse_death_age": 85,
        "initial_roth_balance": 200000, "initial_trad_balance": 1500000,
        "growth_rate": 0.05, "married_ss_income": 40000,
        "single_ss_income": 25000, "pension_income": 0, "withdrawal_rate": 0.12
    }
    for strat in ["A", "B"]:
        results = simulate_retirement(**test_params, strategy=strat)
        print(f"Strategy {strat}: Ending Balance ${results[-1]['Roth Balance'] + results[-1]['Traditional Balance']:,.2f}")
