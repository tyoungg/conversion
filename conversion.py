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
# SIMULATION ENGINE
# -----------------------------
def simulate_retirement(
    start_age,
    end_age,
    spouse_death_age,
    initial_roth_balance,
    initial_trad_balance,
    growth_rate,
    ss_income,
    withdrawal_rate,
    married_brackets,
    single_brackets,
    married_deduction,
    single_deduction,
    strategy="B"  # "A" = stop at 22%, "B" = go into 24%
):
    results = []
    roth_balance = initial_roth_balance
    trad_balance = initial_trad_balance

    for age in range(start_age, end_age + 1):
        # Filing status switch
        filing_status = "married" if age < spouse_death_age else "single"
        brackets = married_brackets if filing_status == "married" else single_brackets
        deduction = married_deduction if filing_status == "married" else single_deduction

        # Upper bound of the 22% bracket (start of 24% bracket)
        limit_22pct = brackets[2][1] if len(brackets) > 2 else 999999999

        # Grow accounts at start of year
        roth_balance *= (1 + growth_rate)
        trad_balance *= (1 + growth_rate)

        # Determine target withdrawal (based on initial trad withdrawal logic or fixed spending)
        # For this tool, let's assume the user wants to withdraw a % of their *total* initial-year equivalent?
        # Let's stick to the user's implicit logic: target is what a standard withdrawal would be.
        target_withdrawal = trad_balance * withdrawal_rate

        actual_withdrawal_trad = 0
        actual_withdrawal_roth = 0

        if strategy == "B":
            # Strategy B: Traditional first, then Roth
            actual_withdrawal_trad = min(target_withdrawal, trad_balance)
            trad_balance -= actual_withdrawal_trad

            remainder = target_withdrawal - actual_withdrawal_trad
            actual_withdrawal_roth = min(remainder, roth_balance)
            roth_balance -= actual_withdrawal_roth
        else:
            # Strategy A: Stop at 22% bracket
            # We need to find max W_trad such that:
            # (W_trad + TaxableSS(W_trad) - Deduction) <= limit_22pct

            # Simple binary search for W_trad
            low = 0
            high = target_withdrawal
            best_w_trad = 0

            for _ in range(20):
                mid = (low + high) / 2
                taxable_ss = calculate_taxable_ss(mid, ss_income, filing_status)
                taxable_income = max(0, mid + taxable_ss - deduction)

                if taxable_income <= limit_22pct:
                    best_w_trad = mid
                    low = mid
                else:
                    high = mid

            actual_withdrawal_trad = min(best_w_trad, trad_balance)
            trad_balance -= actual_withdrawal_trad

            # Remainder from Roth
            needed_from_roth = target_withdrawal - actual_withdrawal_trad
            actual_withdrawal_roth = min(needed_from_roth, roth_balance)
            roth_balance -= actual_withdrawal_roth

        # Calculate taxes for the year
        taxable_ss = calculate_taxable_ss(actual_withdrawal_trad, ss_income, filing_status)
        taxable_income = max(0, actual_withdrawal_trad + taxable_ss - deduction)
        taxes = calculate_tax(taxable_income, brackets)

        total_income = ss_income + actual_withdrawal_trad + actual_withdrawal_roth
        net_income = total_income - taxes

        results.append({
            "Age": age,
            "Filing Status": filing_status,
            "Roth Balance": roth_balance,
            "Traditional Balance": trad_balance,
            "Withdrawal Trad": actual_withdrawal_trad,
            "Withdrawal Roth": actual_withdrawal_roth,
            "Total Income": total_income,
            "Taxes": taxes,
            "Net Income": net_income
        })

    return results


# -----------------------------
# USER INPUTS
# -----------------------------
params = {
    "start_age": 65,
    "end_age": 95,
    "spouse_death_age": 85,
    "initial_roth_balance": 200000,
    "initial_trad_balance": 1500000, # Increased for 24% testing
    "growth_rate": 0.05,
    "ss_income": 40000,
    "withdrawal_rate": 0.12,
    "married_brackets": [
        (0, 22000, 0.10),
        (22000, 89450, 0.12),
        (89450, 190750, 0.22),
        (190750, 364200, 0.24),
    ],
    "single_brackets": [
        (0, 11000, 0.10),
        (11000, 44725, 0.12),
        (44725, 95375, 0.22),
        (95375, 182100, 0.24),
    ],
    "married_deduction": 29200,
    "single_deduction": 14600
}

# -----------------------------
# RUN SCENARIOS
# -----------------------------
results_a = simulate_retirement(**params, strategy="A")
results_b = simulate_retirement(**params, strategy="B")

def summarize(results):
    total_taxes = sum(r["Taxes"] for r in results)
    ending_balance = results[-1]["Roth Balance"] + results[-1]["Traditional Balance"]
    return total_taxes, ending_balance

tax_a, bal_a = summarize(results_a)
tax_b, bal_b = summarize(results_b)

print(f"Scenario A (Stop at 22%): Total Taxes = ${tax_a:,.2f}, Ending Balance = ${bal_a:,.2f}")
print(f"Scenario B (Go into 24%): Total Taxes = ${tax_b:,.2f}, Ending Balance = ${bal_b:,.2f}")

if pd is not None:
    df_a = pd.DataFrame(results_a)
    print("\nScenario A Head:")
    print(df_a.head())

# -----------------------------
# VISUALIZATION (If possible)
# -----------------------------
if plt is not None:
    plt.figure(figsize=(10, 6))
    ages = [r["Age"] for r in results_a]
    plt.plot(ages, [r["Roth Balance"] + r["Traditional Balance"] for r in results_a], label="Total Balance (Scenario A)")
    plt.plot(ages, [r["Roth Balance"] + r["Traditional Balance"] for r in results_b], label="Total Balance (Scenario B)", linestyle='--')
    plt.xlabel("Age")
    plt.ylabel("Balance")
    plt.title("Retirement Strategy Comparison")
    plt.legend()
    plt.show()
