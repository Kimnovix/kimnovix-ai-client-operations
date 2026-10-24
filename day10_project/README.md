# Kiambu Dairy Co-op Payment Calculator

A command-line payout calculation tool built for dairy co-operative collection centres to calculate daily farmer milk payments against a configurable weekly buying rate.

## Files Included

* **`dairy_calculator.py`:** Prompts for the farmer's name and litres supplied, validates the input, and outputs a formatted KES payout receipt.
* **`price.txt`:** Plain-text configuration file storing the current weekly buying price per litre (default: `55.0`).

## Setup & Usage

1. **Run the calculator:**
   ```bash
   python3 day10_project/dairy_calculator.py
   ```

2. **Update the weekly milk price:**
   Open `day10_project/price.txt`, replace the number with the new weekly rate per litre (e.g., `58.5`), and save the file. No code changes are required.

## Example Output

```text
==========================================
   KIAMBU DAIRY CO-OP PAYMENT CALCULATOR  
==========================================
Current buying price: KES 55.00 per litre

Farmer name: John Kamau
Litres supplied today: 42.5

--- PAYMENT SUMMARY ---
Farmer : John Kamau
Litres : 42.50 L
Rate   : KES 55.00 / litre
Total  : KES 2,337.50
-----------------------
```