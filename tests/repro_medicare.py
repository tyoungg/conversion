import json
from docs.conversion import simulate_retirement

def test_medicare_different_ages():
    params = {
        "start_age": 60,
        "end_age": 70,
        "spouse_death_age": 90,
        "initial_roth_balance": 0,
        "initial_trad_balance": 1000000,
        "growth_rate": 0,
        "pension_income": 0,
        "withdrawal_rate": 0.04,
        "ss_primary_fra": 0,
        "birth_year_primary": 1965,
        "claim_age_primary": 70,
        "ss_spouse_fra": 0,
        "birth_year_spouse": 1970, # Spouse is 5 years younger
        "claim_age_spouse": 70,
        "filing_status": "married",
        "include_medicare": True,
        "enable_roth_conversion": False
    }

    results = simulate_retirement(**params, strategy="A")

    for r in results:
        age = r["Age"]
        # Primary age 65 should pay Medicare
        # Spouse age = age - (1970 - 1965) = age - 5
        # When primary is 65, spouse is 60. Spouse should NOT pay Medicare.
        # Current logic doubles it for MFJ if age >= 65.

        spouse_age = age - 5
        print(f"Age {age} (Spouse {spouse_age}): Medicare Cost = {r['Medicare Cost']}, MAGI = {r['MAGI']}")

        if age == 65:
            # Expected: only primary pays.
            # 2025 base is $185. Annual = 185 * 12 = 2220.
            # Current code probably says 2220 * 2 = 4440.
            pass

if __name__ == "__main__":
    test_medicare_different_ages()
