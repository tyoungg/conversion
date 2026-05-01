
from docs.conversion import calculate_medicare_premium

def test_irmaa():
    # Single 2025
    # Standard: <= 106,000 -> 185.00
    # Tier 2: 106,001 to 133,000 -> 259.00
    # Tier 5: >= 500,000 -> 628.90

    print(f"MAGI 106,000: {calculate_medicare_premium(106000, 'single', 65)/12}")
    print(f"MAGI 106,001: {calculate_medicare_premium(106001, 'single', 65)/12}")
    print(f"MAGI 499,999: {calculate_medicare_premium(499999, 'single', 65)/12}")
    print(f"MAGI 500,000: {calculate_medicare_premium(500000, 'single', 65)/12}")

if __name__ == "__main__":
    test_irmaa()
