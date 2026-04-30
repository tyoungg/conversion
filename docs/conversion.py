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


def calculate_taxable_ss(trad_income, other_income, ss_income, filing_status):
    provisional = trad_income + other_income + 0.5 * ss_income

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


def calculate_medicare_premium(magi, filing_status, age):
    if age < 65:
        return 0

    if filing_status == "married":
        brackets = [194000, 246000, 306000, 366000]
    else:
        brackets = [97000, 123000, 153000, 183000]

    premiums = [164.90, 230.80, 321.80, 412.70, 503.70]

    for i, b in enumerate(brackets):
        if magi <= b:
            return premiums[i] * 12
    return premiums[-1] * 12


def calculate_rmd(balance, age):
    if age < 73 or balance <= 0:
        return 0

    divisors = {
        73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
        78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5,
        83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2, 87: 14.4,
        88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8,
        93: 10.1, 94: 9.5, 95: 8.9
    }

    divisor = divisors.get(age, 8.0)
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
    married_brackets=None,
    single_brackets=None,
    married_deduction=29200,
    single_deduction=14600,
    strategy="B",
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

    roth = initial_roth_balance
    trad = initial_trad_balance
    prev_trad = trad

    results = []
    total_rmd_penalty = 0

    for age in range(start_age, end_age + 1):

        # Filing status
        married = age < spouse_death_age
        filing = "married" if married else "single"
        brackets = married_brackets if married else single_brackets
        deduction = married_deduction if married else single_deduction
        ss = married_ss_income if married else single_ss_income

        # Growth
        roth *= (1 + growth_rate)
        trad *= (1 + growth_rate)

        # RMD
        rmd = calculate_rmd(prev_trad, age) if include_rmd else 0

        # Target bracket cap
        cap_index = 2 if strategy == "A" else 3
        tax_cap = brackets[cap_index][1] if len(brackets) > cap_index else 1e9

        # Binary search for max trad income within cap
        low, high = 0, trad
        best = 0

        for _ in range(25):
            mid = (low + high) / 2
            t_ss = calculate_taxable_ss(mid, pension_income, ss, filing)
            taxable = max(0, mid + pension_income + t_ss - deduction)

            if taxable <= tax_cap:
                best = mid
                low = mid
            else:
                high = mid

        # -------------------------
        # 1. RMD DISTRIBUTION
        # -------------------------
        rmd_dist = min(rmd, trad)
        trad -= rmd_dist

        # -------------------------
        # 2. CONVERSION (fills bracket)
        # -------------------------
        remaining_space = max(0, best - rmd_dist)
        conversion = min(remaining_space, trad)
        trad -= conversion
        roth += conversion

        # -------------------------
        # 3. SPENDING
        # -------------------------
        portfolio = trad + roth
        spend_goal = portfolio * withdrawal_rate

        trad_spend = min(spend_goal, trad)
        trad -= trad_spend

        remaining = spend_goal - trad_spend
        roth_spend = min(remaining, roth)
        roth -= roth_spend

        # -------------------------
        # TAXES
        # -------------------------
        trad_total = rmd_dist + conversion + trad_spend

        taxable_ss = calculate_taxable_ss(trad_total, pension_income, ss, filing)
        taxable_income = max(0, trad_total + pension_income + taxable_ss - deduction)

        taxes = calculate_tax(taxable_income, brackets)

        # -------------------------
        # RMD PENALTY
        # -------------------------
        shortfall = max(0, rmd - rmd_dist)
        penalty = 0.25 * shortfall
        total_rmd_penalty += penalty

        taxes += penalty

        # -------------------------
        # MEDICARE (MAGI includes conversion!)
        # -------------------------
        magi = trad_total + pension_income + taxable_ss
        medicare = calculate_medicare_premium(magi, filing, age) if include_medicare else 0

        # -------------------------
        # INCOME
        # -------------------------
        gross = ss + pension_income + trad_total + roth_spend
        net = gross - taxes - medicare

        results.append({
            "Age": age,
            "Filing Status": filing,
            "RMD": rmd,
            "RMD Taken": rmd_dist,
            "RMD Shortfall": shortfall,
            "Conversion": conversion,
            "Trad Spend": trad_spend,
            "Roth Spend": roth_spend,
            "Traditional Balance": trad,
            "Roth Balance": roth,
            "Taxes": taxes,
            "Medicare": medicare,
            "Net Income": net
        })

        prev_trad = trad

    return results, total_rmd_penalty


# -----------------------------
# QUICK TEST
# -----------------------------
if __name__ == "__main__":

    params = dict(
        start_age=65,
        end_age=95,
        spouse_death_age=85,
        initial_roth_balance=200000,
        initial_trad_balance=1500000,
        growth_rate=0.05,
        married_ss_income=40000,
        single_ss_income=25000,
        pension_income=0,
        withdrawal_rate=0.12
    )

    a, pen_a = simulate_retirement(**params, strategy="A")
    b, pen_b = simulate_retirement(**params, strategy="B")

    def summarize(r, pen):
        taxes = sum(x["Taxes"] for x in r)
        medicare = sum(x["Medicare"] for x in r)
        end_bal = r[-1]["Traditional Balance"] + r[-1]["Roth Balance"]
        return taxes, medicare, end_bal, pen

    print("A:", summarize(a, pen_a))
    print("B:", summarize(b, pen_b))
