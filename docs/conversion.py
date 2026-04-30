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
    provisional = withdrawal_trad + other_income + 0.5 * ss_income

    if filing_status == "married":
        t1, t2 = 32000, 44000
    else:
        t1, t2 = 25000, 34000

    if provisional < t1:
        return 0
    elif provisional < t2:
        return 0.5 * ss_income
    else:
        return 0.85 * ss_income


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
    include_medicare=True
):
    married_brackets = [
        (0, 22000, 0.10),
        (22000, 89450, 0.12),
        (89450, 190750, 0.22),
        (190750, 364200, 0.24),
    ]

    single_brackets = [
        (0, 11000, 0.10),
        (11000, 44725, 0.12),
        (44725, 95375, 0.22),
        (95375, 182100, 0.24),
    ]

    results = []
    roth = initial_roth_balance
    trad = initial_trad_balance
    prev_trad = initial_trad_balance

    for age in range(start_age, end_age + 1):

        married = age < spouse_death_age
        status = "married" if married else "single"
        ss = married_ss_income if married else single_ss_income

        brackets = married_brackets if married else single_brackets
        deduction = 29200 if married else 14600

        limit = brackets[2][1] if strategy == "A" else brackets[3][1]

        # Grow
        roth *= (1 + growth_rate)
        trad *= (1 + growth_rate)

        # -------------------------
        # STEP 1: RMD (MANDATORY)
        # -------------------------
        rmd = calculate_rmd(prev_trad, age) if include_rmd else 0
        rmd_taken = min(rmd, trad)

        trad -= rmd_taken  # MUST leave account

        # -------------------------
        # STEP 2: SPENDING NEED
        # -------------------------
        spending_target = (trad + roth) * withdrawal_rate
        remaining_spending = max(0, spending_target - rmd_taken)

        # -------------------------
        # STEP 3: OPTIMIZE ADDITIONAL TRAD
        # -------------------------
        low, high = 0, 1_000_000
        best_extra = 0

        for _ in range(20):
            mid = (low + high) / 2

            test_trad = rmd_taken + mid

            t_ss = calculate_taxable_ss(test_trad, pension_income, ss, status)
            t_income = max(0, test_trad + pension_income + t_ss - deduction)

            if t_income <= limit:
                best_extra = mid
                low = mid
            else:
                high = mid

        extra_trad = min(best_extra, trad)
        trad -= extra_trad

        total_trad = rmd_taken + extra_trad

        # -------------------------
        # STEP 4: ROTH FOR SPENDING
        # -------------------------
        roth_used = min(remaining_spending, roth)
        roth -= roth_used

        # -------------------------
        # STEP 5: TAXES
        # -------------------------
        taxable_ss = calculate_taxable_ss(total_trad, pension_income, ss, status)
        taxable_income = max(0, total_trad + pension_income + taxable_ss - deduction)

        taxes = calculate_tax(taxable_income, brackets)

        # -------------------------
        # STEP 6: MEDICARE (MAGI)
        # -------------------------
        magi = total_trad + pension_income + taxable_ss
        medicare = calculate_medicare_premium(magi, status, age) if include_medicare else 0

        # -------------------------
        # STEP 7: RMD PENALTY
        # -------------------------
        shortfall = max(0, rmd - total_trad)
        penalty = shortfall * 0.25  # SECURE 2.0 simplified

        # -------------------------
        # FINAL
        # -------------------------
        total_income = total_trad + roth_used + ss + pension_income
        net_income = total_income - (taxes + medicare + penalty)

        prev_trad = trad

        results.append({
            "Age": age,
            "Filing Status": status,
            "Social Security": ss,
            "Pension": pension_income,
            "Traditional Withdrawal": total_trad,
            "Roth Withdrawal": roth_used,
            "Traditional Balance": trad,
            "Roth Balance": roth,
            "RMD Required": rmd,
            "RMD Penalty": penalty,
            "Taxes": taxes,
            "Medicare Cost": medicare,
            "Net Income": net_income
        })

    return results
