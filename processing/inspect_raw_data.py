"""Inspect fields and basic quality statistics in the latest raw FDA file."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIRECTORY = PROJECT_ROOT / "data" / "raw"


def get_latest_raw_file() -> Path:
    """Return the most recently created raw FDA JSON file."""

    raw_files = list(
        RAW_DATA_DIRECTORY.glob("food_enforcement_*.json")
    )

    if not raw_files:
        raise FileNotFoundError(
            f"No raw FDA files found in {RAW_DATA_DIRECTORY}"
        )

    return max(raw_files, key=lambda file_path: file_path.stat().st_mtime)


def load_records(file_path: Path) -> list[dict[str, Any]]:
    """Load recall records from the raw FDA response."""

    with file_path.open("r", encoding="utf-8") as input_file:
        payload = json.load(input_file)

    records = payload.get("results")

    if not isinstance(records, list):
        raise ValueError(
            "The raw file does not contain a valid results list."
        )

    return records


def inspect_records(records: list[dict[str, Any]]) -> None:
    """Print field names and basic data-quality information."""

    all_fields: set[str] = set()

    for record in records:
        all_fields.update(record.keys())

    print(f"Total records inspected: {len(records)}")
    print(f"Total unique fields: {len(all_fields)}")

    print("\nAvailable fields:")
    for field_name in sorted(all_fields):
        print(f"- {field_name}")

    print("\nMissing-value counts:")

    for field_name in sorted(all_fields):
        missing_count = sum(
            1
            for record in records
            if record.get(field_name) in (None, "", [], {})
        )

        print(
            f"{field_name}: "
            f"{missing_count} missing out of {len(records)}"
        )

    classifications = Counter(
        record.get("classification", "Unknown")
        for record in records
    )

    statuses = Counter(
        record.get("status", "Unknown")
        for record in records
    )

    states = Counter(
        record.get("state", "Unknown")
        for record in records
    )

    print("\nClassification distribution:")
    for classification, count in classifications.most_common():
        print(f"- {classification}: {count}")

    print("\nStatus distribution:")
    for status, count in statuses.most_common():
        print(f"- {status}: {count}")

    print("\nTop states:")
    for state, count in states.most_common(10):
        print(f"- {state}: {count}")


def main() -> None:
    """Run the inspection."""

    latest_file = get_latest_raw_file()

    print(f"Inspecting file: {latest_file}")

    records = load_records(latest_file)
    inspect_records(records)


if __name__ == "__main__":
    main()