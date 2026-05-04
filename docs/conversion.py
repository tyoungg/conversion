# -----------------------------
# SOCIAL SECURITY LOGIC
# -----------------------------
def get_fra(birth_year):
    """Returns Full Retirement Age (FRA) in years and months based on birth year."""
    if birth_year <= 1937:
        return 65, 0
    if birth_year == 1938:
        return 65, 2
    if birth_year == 1939:
        return 65, 4
    if birth_year == 1940:
        return 65, 6
    if birth_year == 1941:
        return 65, 8
    if birth_year == 1942:
        return 65, 10
    if 1943 <= birth_year <= 1954:
        return 66, 0
    if birth_year == 1955:
        return 66, 2
    if birth_year == 1956:
        return 66, 4
    if birth_year == 1957:
        return 66, 6
    if birth_year == 1958:
        return 66, 8
    if birth_year == 1959:
        return 66, 10
    return 67, 0

def calculate_adjusted_ss(monthly_fra_benefit, claim_age, birth_year):
    """Calculates the adjusted monthly Social Security benefit based on claiming age."""
    fra_years, fra_months = get_fra(birth_year)
    fra_total_months = fra_years * 12 + fra_months
    claim_total_months = int(claim_age * 12)

    diff_months = claim_total_months - fra_total_months

    if diff_months == 0:
        return monthly_fra_benefit

    if diff_months > 0:
        # Delayed Retirement Credits: 8% per year (2/3 of 1% per month)
        # Only up to age 70
        months_to_70 = min(diff_months, (70 * 12) - fra_total_months)
        return monthly_fra_benefit * (1 + (months_to_70 * (2/3 / 100)))
    else:
        # Reduction for early claiming
        # 5/9 of 1% for each month up to 36 months
        # 5/12 of 1% for each month beyond 36 months
        months_early = abs(diff_months)
        reduction = 0
        if months_early <= 36:
            reduction = months_early * (5/9 / 100)
        else:
            reduction = (36 * (5/9 / 100)) + ((months_early - 36) * (5/12 / 100))
        return monthly_fra_benefit * (1 - reduction)

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
    pension_income,
    withdrawal_rate,
    strategy="B",
    include_rmd=True,
    include_medicare=True,
    fixed_roth_withdrawal=0,
    use_roth_buffer=True,
    enable_roth_conversion=True,
    qcd_percentage=0,
    # New SS Parameters
    filing_status="married",
    ss_primary_fra=3000,
    birth_year_primary=1960,
    claim_age_primary=67,
    ss_spouse_fra=1500,
    birth_year_spouse=1962,
    claim_age_spouse=67,
    **kwargs
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

    # Gross Withdrawal Target
    gross_withdrawal_target = (initial_trad_balance + initial_roth_balance) * withdrawal_rate

    # Calculate individual SS benefits once
    benefit_primary = calculate_adjusted_ss(ss_primary_fra, claim_age_primary, birth_year_primary)

    if filing_status == "married":
        benefit_spouse_own = calculate_adjusted_ss(ss_spouse_fra, claim_age_spouse, birth_year_spouse)
        # Spousal benefit: up to 50% of primary's FRA benefit
        # (Reduced if spouse claims before their own FRA)
        potential_spousal = ss_primary_fra * 0.5
        # Reduction factor for early spousal claiming (simplified)
        spouse_fra_y, spouse_fra_m = get_fra(birth_year_spouse)
        spouse_fra_total = spouse_fra_y * 12 + spouse_fra_m
        spouse_claim_total = claim_age_spouse * 12
        if spouse_claim_total < spouse_fra_total:
            months_early = spouse_fra_total - spouse_claim_total
            # Spousal reduction is 25/36 of 1% for first 36 months, then 5/12 of 1%
            if months_early <= 36:
                red = months_early * (25/36 / 100)
            else:
                red = (36 * (25/36 / 100)) + ((months_early - 36) * (5/12 / 100))
            potential_spousal *= (1 - red)

        benefit_spouse = max(benefit_spouse_own, potential_spousal)
    else:
        benefit_spouse = 0

    # SECURE 2.0 RMD Age Logic
    current_birth_year = 2025 - start_age
    rmd_start_age = 75 if current_birth_year >= 1960 else 73

    for age in range(start_age, end_age + 1):
        married = age <= spouse_death_age and filing_status == "married"
        status = "married" if married else "single"

        # Determine SS income for this age
        current_ss = 0
        if age >= claim_age_primary:
            current_ss += benefit_primary * 12

        if filing_status == "married":
            # Spouse age = Primary age - (Spouse Birth Year - Primary Birth Year)
            # Example: Primary 1960, Spouse 1962. At Primary age 65, Spouse is 63.
            # 65 - (1962 - 1960) = 63. Correct.
            spouse_age = age - (birth_year_spouse - birth_year_primary)
            if married:
                if spouse_age >= claim_age_spouse:
                    current_ss += benefit_spouse * 12
            else:
                # Survivor benefit: Higher of primary or spouse
                current_ss = max(benefit_primary, benefit_spouse) * 12

        ss = current_ss
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

        # 3. Withdrawal Logic: Prioritize Traditional to meet target
        remaining_target = max(0, gross_withdrawal_target - qcd_amount - rmd_taken)
        trad_for_target = min(trad, remaining_target)
        trad -= trad_for_target
        current_trad_wd = rmd_taken + trad_for_target

        # 4. Roth Withdrawal (Buffer if Trad was insufficient for target)
        remaining_target = max(0, gross_withdrawal_target - qcd_amount - current_trad_wd)
        roth_wd = fixed_roth_withdrawal
        if use_roth_buffer:
            roth_wd += remaining_target

        roth_wd = min(roth, roth_wd)
        roth -= roth_wd

        # 5. Conversion Logic (Top off bracket if enabled)
        roth_conv = 0
        best_surplus = 0
        if enable_roth_conversion:
            low, high = 0, trad
            for _ in range(40):
                mid = (low + high) / 2
                t_inc, _, _ = get_tax_data(current_trad_wd + mid)
                if t_inc <= bracket_limit - 1:
                    best_surplus = mid
                    low = mid
                else:
                    high = mid

            if best_surplus > 0:
                _, taxes_now, med_now = get_tax_data(current_trad_wd + best_surplus)
                _, taxes_base, med_base = get_tax_data(current_trad_wd)

                shortfall_now = max(0, rmd - (current_trad_wd + best_surplus + qcd_amount))
                shortfall_base = max(0, rmd - (current_trad_wd + qcd_amount))
                penalty_now = shortfall_now * 0.25
                penalty_base = shortfall_base * 0.25

                net_now = (current_trad_wd + best_surplus + ss + pension_income + roth_wd) - (taxes_now + med_now + penalty_now)
                net_base = (current_trad_wd + ss + pension_income + roth_wd) - (taxes_base + med_base + penalty_base)

                if net_now > net_base:
                    roth_conv = net_now - net_base
                    trad -= best_surplus
                    roth += roth_conv

        total_withdrawn_this_year = current_trad_wd + (best_surplus if roth_conv > 0 else 0)
        taxable_income, taxes, medicare = get_tax_data(total_withdrawn_this_year)
        shortfall = max(0, rmd - (total_withdrawn_this_year + qcd_amount))
        penalty = shortfall * 0.25
        net_income = (total_withdrawn_this_year + ss + pension_income + roth_wd) - (taxes + medicare + penalty + roth_conv)

        prev_trad = trad

        results.append({
            "Age": age,
            "Filing Status": status,
            "Social Security": ss,
            "Pension": pension_income,
            "Taxable Trad W/D": total_withdrawn_this_year,
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
            "Total Outflow": total_withdrawn_this_year + roth_wd + qcd_amount
        })

    return results


if __name__ == "__main__":
    test_params = {
        "start_age": 65, "end_age": 95, "spouse_death_age": 85,
        "initial_roth_balance": 200000, "initial_trad_balance": 1500000,
        "growth_rate": 0.05, "pension_income": 0, "withdrawal_rate": 0.12,
        "ss_primary_fra": 3000, "birth_year_primary": 1960, "claim_age_primary": 67
    }
    for strat in ["A", "B"]:
        results = simulate_retirement(**test_params, strategy=strat)
        print(f"Strategy {strat}: Ending Balance ${results[-1]['Roth Balance'] + results[-1]['Traditional Balance']:,.2f}")
