import pandas as pd
import matplotlib.pyplot as plt


# -----------------------------
# TAX FUNCTION
# -----------------------------
def calculate_tax(income, brackets):
    tax = 0
    for lower, upper, rate in brackets:
        if income > lower:
            taxed_amount = min(income, upper) - lower
            tax += taxed_amount * rate
        else:
            break
    return tax


# -----------------------------
# SIMULATION ENGINE
# -----------------------------
def simulate_retirement(
    start_age,
    end_age,
    spouse_death_age,
    roth_balance,
    trad_balance,
    growth_rate,
    ss_income,
    withdrawal_rate,
    married_brackets,
    single_brackets
):
    results = []

    for age in range(start_age, end_age + 1):

        # Filing status switch
        filing_status = "married" if age < spouse_death_age else "single"
        brackets = married_brackets if filing_status == "married" else single_brackets

        # Grow accounts
        roth_balance *= (1 + growth_rate)
        trad_balance *= (1 + growth_rate)

        # Withdraw from traditional
        withdrawal = trad_balance * withdrawal_rate
        trad_balance -= withdrawal

        # Income
        total_income = ss_income + withdrawal

        # Taxable income (simplified for now)
        taxable_income = withdrawal

        taxes = calculate_tax(taxable_income, brackets)
        net_income = total_income - taxes

        results.append({
            "Age": age,
            "Filing Status": filing_status,
            "Roth Balance": roth_balance,
            "Traditional Balance": trad_balance,
            "Withdrawal": withdrawal,
            "Total Income": total_income,
            "Taxes": taxes,
            "Net Income": net_income
        })

    return pd.DataFrame(results)


# -----------------------------
# USER INPUTS (EDIT THESE)
# -----------------------------
start_age = 65
end_age = 95
spouse_death_age = 85

roth_balance = 200000
trad_balance = 500000

growth_rate = 0.05
ss_income = 40000
withdrawal_rate = 0.04


# Example tax brackets (you can customize)
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


# -----------------------------
# RUN SIMULATION
# -----------------------------
df = simulate_retirement(
    start_age,
    end_age,
    spouse_death_age,
    roth_balance,
    trad_balance,
    growth_rate,
    ss_income,
    withdrawal_rate,
    married_brackets,
    single_brackets
)


# -----------------------------
# OUTPUT
# -----------------------------
print(df.head(10))


# -----------------------------
# VISUALIZATION
# -----------------------------
plt.figure()
plt.plot(df["Age"], df["Roth Balance"], label="Roth")
plt.plot(df["Age"], df["Traditional Balance"], label="Traditional")
plt.xlabel("Age")
plt.ylabel("Balance")
plt.title("Retirement Account Balances")
plt.legend()
plt.show()
