#!/usr/bin/env python3
"""
Format ModSecurity log files by extracting unparsed rules into trace files.

This script reads a ModSecurity log file in JSON format and creates trace files
for each transaction containing the unparsed rules in order of appearance.

Supported formats:
- Single JSON object (one transaction)
- JSON array of transactions
- NDJSON (Newline Delimited JSON) - one transaction per line
"""

import argparse
import json
import sys
from pathlib import Path


def extract_unparsed_rules(transaction_data: dict) -> list[str]:
    """Extract all unparsed rules from a transaction in order of appearance."""
    unparsed_rules = []

    matched_rules = transaction_data.get("matched_rules", [])
    for rule_group in matched_rules:
        rules = rule_group.get("rules", [])
        for rule in rules:
            unparsed = rule.get("unparsed")
            if unparsed:
                unparsed_rules.append(unparsed)

    return unparsed_rules


def process_transaction(transaction_data: dict, traces_dir: Path) -> tuple[str | None, dict]:
    """Process a single transaction and write its trace file.

    Returns a tuple of (transaction_id, cleaned_transaction).
    transaction_id is None if processing failed.
    cleaned_transaction has matched_rules removed.
    """
    transaction_info = transaction_data.get("transaction", {})
    transaction_id = transaction_info.get("transaction_id")

    # Create cleaned transaction without matched_rules
    cleaned_transaction = {k: v for k, v in transaction_data.items() if k != "matched_rules"}

    if not transaction_id:
        return None, cleaned_transaction

    unparsed_rules = extract_unparsed_rules(transaction_data)

    if unparsed_rules:
        trace_file = traces_dir / f"{transaction_id}.txt"
        trace_file.write_text("\n".join(unparsed_rules))

    return transaction_id, cleaned_transaction


def load_transactions(log_file: Path) -> list[dict]:
    """Load transactions from a JSON or NDJSON file."""
    content = log_file.read_text(encoding="utf-8", errors="replace")

    # Try parsing as regular JSON first (single object or array)
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "transaction" in data:
            return [data]
    except json.JSONDecodeError:
        pass

    # Try parsing as NDJSON (one JSON object per line)
    transactions = []
    for line_num, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if isinstance(data, dict) and "transaction" in data:
                transactions.append(data)
        except json.JSONDecodeError as e:
            print(f"Warning: Skipping invalid JSON at line {line_num}: {e}", file=sys.stderr)

    return transactions


def main():
    parser = argparse.ArgumentParser(
        description="Extract unparsed ModSecurity rules from JSON log into trace files"
    )
    parser.add_argument(
        "log_file",
        type=Path,
        help="Path to the ModSecurity log file in JSON or NDJSON format"
    )
    args = parser.parse_args()

    log_file: Path = args.log_file

    if not log_file.exists():
        print(f"Error: File not found: {log_file}", file=sys.stderr)
        sys.exit(1)

    # Create traces directory in the same folder as the log file
    traces_dir = log_file.parent / "traces"
    traces_dir.mkdir(exist_ok=True)

    transactions = load_transactions(log_file)

    if not transactions:
        print("Error: No valid transactions found in the file.", file=sys.stderr)
        sys.exit(1)

    processed_count = 0
    cleaned_transactions = []

    for transaction_data in transactions:
        transaction_id, cleaned = process_transaction(transaction_data, traces_dir)
        cleaned_transactions.append(cleaned)
        if transaction_id:
            processed_count += 1
            print(f"Created trace: {transaction_id}.txt")

    # Save cleaned transactions (without matched_rules) to a new file
    cleaned_file = log_file.parent / f"{log_file.stem}_cleaned.json"
    with open(cleaned_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_transactions, f, indent=2)

    print(f"\nProcessed {processed_count} transaction(s). Traces saved to: {traces_dir}")
    print(f"Cleaned JSON saved to: {cleaned_file}")


if __name__ == "__main__":
    main()
