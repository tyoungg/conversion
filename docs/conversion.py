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


def calculate_taxable_ss(trad_income, pension_income, ss_income, filing_status):
    provisional = trad_income + pension_income + 0.5 * ss_income

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
# MEDICARE
# -----------------------------
def calculate_medicare(magi, filing_status, age):
    if age < 65:
        return 0

    if filing_status == "married":
        brackets = [194000, 246000, 306000, 366000]
    else:
        brackets = [97000, 123000, 153000, 183000]

    premiums = [164.9, 230.8, 321.8, 412.7, 503.7]

    for i, limit in enumerate(brackets):
        if magi <= limit:
            return premiums[i] * 12

    return premiums[-1] * 12


# -----------------------------
# RMD
# -----------------------------
def calculate_rmd(balance, age):
    if age < 73 or balance <= 0:
        return 0

    divisors = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7,
        77: 22.9, 78: 22.0, 79: 21.1, 80: 20.2,
        81: 19.4, 82: 18.5, 83: 17.7, 84: 16.8,
        85: 16.0, 86: 15.2, 87: 14.4, 88: 13.7,
        89: 12.9, 90: 12.2
    }

    divisor = divisors.get(age, 10)
    return balance / divisor


# -----------------------------
# MAIN SIM
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
    strategy="B"
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

    married_deduction = 29200
    single_deduction = 14600

    results = []

    roth = initial_roth_balance
    trad = initial_trad_balance

    for age in range(start_age, end_age + 1):

        married = age < spouse_death_age
        filing = "married" if married else "single"

        brackets = married_brackets if married else single_brackets
        deduction = married_deduction if married else single_deduction
        ss = married_ss_income if married else single_ss_income

        # Grow balances
        roth *= (1 + growth_rate)
        trad *= (1 + growth_rate)

        # RMD FIRST (CRITICAL FIX)
        rmd = calculate_rmd(trad, age)
        trad_withdraw = min(rmd, trad)
        trad -= trad_withdraw

        # Determine target withdrawal
        target = (roth + trad) * withdrawal_rate

        # Fill up to tax bracket
        limit = brackets[2][1] if strategy == "A" else brackets[3][1]

        low, high = 0, 500000
        best_extra = 0

        for _ in range(20):
            mid = (low + high) / 2
            t_ss = calculate_taxable_ss(trad_withdraw + mid, pension_income, ss, filing)
            taxable = trad_withdraw + mid + pension_income + t_ss - deduction

            if taxable <= limit:
                best_extra = mid
                low = mid
            else:
                high = mid

        extra_trad = min(best_extra, trad)
        trad -= extra_trad

        trad_total = trad_withdraw + extra_trad

        # Roth if needed
        roth_withdraw = 0
        if trad_total < target:
            roth_withdraw = min(target - trad_total, roth)
            roth -= roth_withdraw

        # Taxes
        t_ss = calculate_taxable_ss(trad_total, pension_income, ss, filing)
        taxable_income = max(0, trad_total + pension_income + t_ss - deduction)
        taxes = calculate_tax(taxable_income, brackets)

        # Medicare (includes ALL income)
        magi = trad_total + pension_income + ss
        medicare = calculate_medicare(magi, filing, age)

        total_income = trad_total + roth_withdraw + ss + pension_income
        net = total_income - taxes - medicare

        results.append({
            "Age": age,
            "Filing Status": filing,
            "Social Security": ss,
            "Pension": pension_income,
            "Traditional Withdrawal": trad_total,
            "Roth Withdrawal": roth_withdraw,
            "Roth Balance": roth,
            "Traditional Balance": trad,
            "RMD Required": rmd,
            "Taxes": taxes,
            "Medicare Cost": medicare,
            "Net Income": net
        })

    return results
