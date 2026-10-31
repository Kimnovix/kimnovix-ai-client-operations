"""
Day 15 (Week 3 Capstone): AI Meeting Notes Summarizer CLI
---------------------------------------------------------
Processes raw, unstructured meeting notes via CLI arguments or interactive input
and outputs structured Decisions Made, Action Items with Owners, and Unresolved Questions.

Usage:
    python3 week3/day15_meeting_summarizer.py "Raw meeting notes here..."
    python3 week3/day15_meeting_summarizer.py
"""

import os
import sys
import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "claude-haiku-4-5-20251001"

# Pricing telemetry constants: $1.00 / 1M input tokens, $5.00 / 1M output tokens
INPUT_COST_PER_M = 1.00
OUTPUT_COST_PER_M = 5.00
USD_TO_KES = 129.79

SYSTEM_PROMPT = """You are an executive operations assistant for Kenyan enterprises, agribusinesses, and engineering teams.
Your sole task is to convert raw, messy meeting notes into a clean, structured operational summary.

You MUST format your output using these exact three sections:

1. DECISIONS MADE
- Bullet points of concrete agreements, approved budgets, or finalized policies. (Write "None recorded." if none exist).

2. ACTION ITEMS & OWNERS
- Bullet points formatted strictly as: [Owner Name/Role] -> [Specific Task] (Deadline: [Timeline/Not specified]).

3. UNRESOLVED QUESTIONS & BLOCKERS
- Bullet points of open issues, pending approvals, or missing data that require follow-up. (Write "None recorded." if none exist).

Rules:
- Be concise, direct, and factual.
- Do not invent owners, budgets, or deadlines not present in the source notes.
- Preserve local context (KES amounts, locations, technical terms).
"""


def calculate_cost_kes(input_tokens: int, output_tokens: int) -> float:
    """Calculates exact API call cost in Kenyan Shillings (KES)."""
    usd_cost = ((input_tokens / 1_000_000) * INPUT_COST_PER_M) + (
        (output_tokens / 1_000_000) * OUTPUT_COST_PER_M
    )
    return usd_cost * USD_TO_KES


def summarize_meeting_notes(raw_notes: str) -> str:
    """Validates input, invokes Claude Haiku 4.5 with timeout, and handles API exceptions."""
    cleaned_notes = raw_notes.strip()
    if not cleaned_notes:
        return "[INPUT ERROR] Meeting notes cannot be empty. Provide raw text to summarize."

    if len(cleaned_notes) < 15:
        return "[INPUT ERROR] Input is too short to be valid meeting notes. Provide more context."

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "[AUTH ERROR] Missing ANTHROPIC_API_KEY. Add it to your root .env file and retry."

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=600,
            timeout=30.0,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Summarize these raw meeting notes:\n\n{cleaned_notes}",
                }
            ],
        )

        if not response.content or not response.content[0].text.strip():
            return "[API ERROR] Empty response received from Claude. Check model status and retry."

        summary_text = response.content[0].text.strip()
        in_tokens = response.usage.input_tokens
        out_tokens = response.usage.output_tokens
        cost_kes = calculate_cost_kes(in_tokens, out_tokens)

        footer = (
            f"\n{'-' * 54}\n"
            f"Telemetry : {in_tokens} input tokens | {out_tokens} output tokens\n"
            f"Est. Cost : KES {cost_kes:.4f} ({MODEL_NAME})\n"
            f"{'=' * 54}"
        )
        return f"{summary_text}\n{footer}"

    except anthropic.AuthenticationError:
        return "[AUTH ERROR] Invalid ANTHROPIC_API_KEY. Verify your key in the .env file or Anthropic Console."
    except anthropic.RateLimitError:
        return "[RATE LIMIT ERROR] API rate limit or credit cap reached. Wait 60 seconds and try again."
    except anthropic.APITimeoutError:
        return "[TIMEOUT ERROR] Request timed out after 30 seconds. Check network stability and retry."
    except anthropic.APIConnectionError:
        return "[NETWORK ERROR] No internet connection. Verify your network interface and try again."
    except Exception as e:
        return f"[UNEXPECTED ERROR] Failed to process meeting notes: {e}"


def main():
    print("======================================================")
    print("     KIMNOVIX AI MEETING NOTES SUMMARIZER (v1.0)      ")
    print("======================================================")

    # Mode 1: Direct CLI Argument Execution (python3 day15_meeting_summarizer.py "notes...")
    if len(sys.argv) >= 2:
        raw_notes = " ".join(sys.argv[1:])
        print("Processing CLI argument payload...\n")
        print(summarize_meeting_notes(raw_notes))
        return

    # Mode 2: Interactive Terminal Fallback
    print("Usage Tip: You can also pass notes directly via CLI:")
    print("  python3 week3/day15_meeting_summarizer.py 'your raw notes here'\n")
    raw_notes = input("Paste raw meeting notes (or 'q' to quit): ").strip()

    if raw_notes.lower() in ["q", "quit", "exit"]:
        print("Exiting summarizer.")
        sys.exit(0)

    print("\nStructuring operational summary...\n")
    print(summarize_meeting_notes(raw_notes))


if __name__ == "__main__":
    main()