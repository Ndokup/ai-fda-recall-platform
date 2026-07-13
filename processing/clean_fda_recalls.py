"""Clean raw openFDA recall records and create a processed CSV dataset."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIRECTORY = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIRECTORY = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE_NAME = "fda_recalls_cleaned.csv"


OUTPUT_COLUMNS = [
    "recall_number",
    "event_id",
    "status",
    "classification",
    "product_type",
    "recalling_firm",
    "product_description",
    "reason_for_recall",
    "product_quantity",
    "code_info",
    "distribution_pattern",
    "city",
    "state",
    "postal_code",
    "country",
    "recall_initiation_date",
    "center_classification_date",
    "report_date",
    "termination_date",
    "initial_firm_notification",
    "voluntary_mandated",
    "source_file",
    "processed_at_utc",
]


def get_latest_raw_file() -> Path:
    """Return the newest raw FDA JSON file."""

    raw_files = list(RAW_DATA_DIRECTORY.glob("food_enforcement_*.json"))

    if not raw_files:
        raise FileNotFoundError(
            f"No raw FDA files found in {RAW_DATA_DIRECTORY}"
        )

    return max(raw_files, key=lambda file_path: file_path.stat().st_mtime)


def load_raw_records(file_path: Path) -> list[dict[str, Any]]:
    """Load the results array from a raw API response."""

    with file_path.open("r", encoding="utf-8") as input_file:
        payload = json.load(input_file)

    records = payload.get("results")

    if not isinstance(records, list):
        raise ValueError(
            "The raw JSON file does not contain a valid results list."
        )

    return records


def clean_text(value: Any) -> str | None:
    """Normalize whitespace and return None for empty values."""

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return re.sub(r"\s+", " ", text)


def clean_uppercase_code(value: Any) -> str | None:
    """Normalize short codes such as state values."""

    cleaned_value = clean_text(value)

    if cleaned_value is None:
        return None

    return cleaned_value.upper()


def parse_fda_date(value: Any) -> str | None:
    """Convert an FDA YYYYMMDD date into ISO YYYY-MM-DD format."""

    cleaned_value = clean_text(value)

    if cleaned_value is None:
        return None

    try:
        parsed_date = datetime.strptime(cleaned_value, "%Y%m%d").date()
    except ValueError:
        return None

    return parsed_date.isoformat()


def clean_record(
    record: dict[str, Any],
    source_file: str,
    processed_at_utc: str,
) -> dict[str, Any]:
    """Select and normalize fields from one FDA record."""

    return {
        "recall_number": clean_text(record.get("recall_number")),
        "event_id": clean_text(record.get("event_id")),
        "status": clean_text(record.get("status")),
        "classification": clean_text(record.get("classification")),
        "product_type": clean_text(record.get("product_type")),
        "recalling_firm": clean_text(record.get("recalling_firm")),
        "product_description": clean_text(record.get("product_description")),
        "reason_for_recall": clean_text(record.get("reason_for_recall")),
        "product_quantity": clean_text(record.get("product_quantity")),
        "code_info": clean_text(record.get("code_info")),
        "distribution_pattern": clean_text(record.get("distribution_pattern")),
        "city": clean_text(record.get("city")),
        "state": clean_uppercase_code(record.get("state")),
        "postal_code": clean_text(record.get("postal_code")),
        "country": clean_text(record.get("country")),
        "recall_initiation_date": parse_fda_date(
            record.get("recall_initiation_date")
        ),
        "center_classification_date": parse_fda_date(
            record.get("center_classification_date")
        ),
        "report_date": parse_fda_date(record.get("report_date")),
        "termination_date": parse_fda_date(record.get("termination_date")),
        "initial_firm_notification": clean_text(
            record.get("initial_firm_notification")
        ),
        "voluntary_mandated": clean_text(record.get("voluntary_mandated")),
        "source_file": source_file,
        "processed_at_utc": processed_at_utc,
    }


def deduplicate_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Remove duplicate records using recall_number."""

    deduplicated_records: dict[str, dict[str, Any]] = {}
    records_without_key: list[dict[str, Any]] = []

    for record in records:
        recall_number = record.get("recall_number")

        if recall_number:
            deduplicated_records[recall_number] = record
        else:
            records_without_key.append(record)

    cleaned_records = list(deduplicated_records.values()) + records_without_key
    duplicates_removed = len(records) - len(cleaned_records)

    return cleaned_records, duplicates_removed


def write_csv(records: list[dict[str, Any]], output_path: Path) -> None:
    """Write cleaned records to a UTF-8 CSV file."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=OUTPUT_COLUMNS,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    """Run the raw-to-processed transformation."""

    latest_raw_file = get_latest_raw_file()
    raw_records = load_raw_records(latest_raw_file)

    processed_at_utc = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    cleaned_records = [
        clean_record(
            record=record,
            source_file=latest_raw_file.name,
            processed_at_utc=processed_at_utc,
        )
        for record in raw_records
    ]

    cleaned_records, duplicates_removed = deduplicate_records(cleaned_records)

    output_path = PROCESSED_DATA_DIRECTORY / OUTPUT_FILE_NAME

    write_csv(records=cleaned_records, output_path=output_path)

    missing_recall_numbers = sum(
        1 for record in cleaned_records if not record.get("recall_number")
    )

    missing_states = sum(
        1 for record in cleaned_records if not record.get("state")
    )

    missing_termination_dates = sum(
        1 for record in cleaned_records if not record.get("termination_date")
    )

    print(f"Raw file: {latest_raw_file}")
    print(f"Raw records read: {len(raw_records)}")
    print(f"Cleaned records written: {len(cleaned_records)}")
    print(f"Duplicate recall numbers removed: {duplicates_removed}")
    print(f"Missing recall numbers: {missing_recall_numbers}")
    print(f"Missing states: {missing_states}")
    print(f"Missing termination dates: {missing_termination_dates}")
    print(f"Processed file: {output_path}")


if __name__ == "__main__":
    main()