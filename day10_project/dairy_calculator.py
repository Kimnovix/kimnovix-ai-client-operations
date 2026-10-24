"""
Dairy Co-op Payment Calculator
------------------------------
Farmer enters their name and litres supplied.
Tool shows total owed at current buying price read from price.txt.

Usage:
    python3 day10_project/dairy_calculator.py

Config:
    Edit day10_project/price.txt to update the weekly rate per litre.
"""

from pathlib import Path

PRICE_FILE = Path(__file__).parent / "price.txt"
DEFAULT_PRICE = 55.0


def get_current_price():
    """Read current buying price from price.txt; fall back to default if missing or invalid."""
    try:
        with open(PRICE_FILE, "r", encoding="utf-8") as file:
            price = float(file.read().strip())
            if price <= 0:
                raise ValueError("Price must be positive.")
            return price
    except (FileNotFoundError, ValueError):
        return DEFAULT_PRICE


def calculate_payment(litres, price_per_litre):
    """Return total payout in KES."""
    return litres * price_per_litre


def run():
    price = get_current_price()

    print("==========================================")
    print("   KIAMBU DAIRY CO-OP PAYMENT CALCULATOR  ")
    print("==========================================")
    print(f"Current buying price: KES {price:,.2f} per litre\n")

    name = input("Farmer name: ").strip()
    if not name:
        print("[INPUT ERROR] Farmer name is required. Exiting.")
        return

    raw_litres = input("Litres supplied today: ").strip()
    try:
        litres = float(raw_litres)
        if litres <= 0:
            print("[INPUT ERROR] Litres supplied must be greater than zero.")
            return
    except ValueError:
        print(f"[INPUT ERROR] '{raw_litres}' is not a valid number. Please enter digits only.")
        return

    total = calculate_payment(litres, price)

    print("\n--- PAYMENT SUMMARY ---")
    print(f"Farmer : {name.title()}")
    print(f"Litres : {litres:,.2f} L")
    print(f"Rate   : KES {price:,.2f} / litre")
    print(f"Total  : KES {total:,.2f}")
    print("-----------------------")


if __name__ == "__main__":
    run()