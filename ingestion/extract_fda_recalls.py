"""Extract food recall records from the openFDA API using pagination."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


BASE_URL = "https://api.fda.gov/food/enforcement.json"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIRECTORY = PROJECT_ROOT / "data" / "raw"

REQUEST_TIMEOUT_SECONDS = 30

PAGE_LIMIT = 100
MAX_RECORDS_TO_EXTRACT = 5000
REQUEST_PAUSE_SECONDS = 0.25


def build_request_parameters(
    limit: int,
    skip: int,
) -> dict[str, str | int]:
    """Create the parameters sent to the openFDA API."""

    parameters: dict[str, str | int] = {
        "limit": limit,
        "skip": skip,
    }

    api_key = os.getenv("OPENFDA_API_KEY")

    if api_key:
        parameters["api_key"] = api_key

    return parameters


def fetch_recall_page(
    limit: int,
    skip: int,
) -> dict[str, Any]:
    """Retrieve one page of recall records from the openFDA API."""

    parameters = build_request_parameters(
        limit=limit,
        skip=skip,
    )

    try:
        response = requests.get(
            BASE_URL,
            params=parameters,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

    except requests.Timeout as error:
        raise RuntimeError(
            f"The request exceeded {REQUEST_TIMEOUT_SECONDS} seconds."
        ) from error

    except requests.HTTPError as error:
        status_code = (
            error.response.status_code
            if error.response is not None
            else "unknown"
        )

        raise RuntimeError(
            f"openFDA returned HTTP status {status_code}: {error}"
        ) from error

    except requests.RequestException as error:
        raise RuntimeError(
            f"Unable to connect to the openFDA API: {error}"
        ) from error

    try:
        payload: dict[str, Any] = response.json()
    except requests.JSONDecodeError as error:
        raise RuntimeError(
            "The openFDA response was not valid JSON."
        ) from error

    results = payload.get("results")

    if not isinstance(results, list):
        raise RuntimeError(
            "The response does not contain the expected results list."
        )

    return payload


def fetch_recall_data_with_pagination() -> dict[str, Any]:
    """Retrieve multiple pages and combine them into one payload."""

    all_records: list[dict[str, Any]] = []
    latest_meta: dict[str, Any] = {}

    for skip in range(
        0,
        MAX_RECORDS_TO_EXTRACT,
        PAGE_LIMIT,
    ):
        print(
            f"Fetching page: skip={skip}, "
            f"limit={PAGE_LIMIT}"
        )

        page_payload = fetch_recall_page(
            limit=PAGE_LIMIT,
            skip=skip,
        )

        page_records = page_payload["results"]
        latest_meta = page_payload.get("meta", {})

        all_records.extend(page_records)

        print(
            f"Records received in this page: "
            f"{len(page_records)}"
        )

        if len(page_records) < PAGE_LIMIT:
            print("Last available page reached.")
            break

        time.sleep(REQUEST_PAUSE_SECONDS)

    combined_payload = {
        "meta": latest_meta,
        "results": all_records,
    }

    return combined_payload


def save_raw_response(payload: dict[str, Any]) -> Path:
    """Save the combined API response as a timestamped JSON file."""

    RAW_DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    extraction_timestamp = datetime.now(timezone.utc)
    filename_timestamp = extraction_timestamp.strftime("%Y%m%dT%H%M%SZ")

    output_path = (
        RAW_DATA_DIRECTORY
        / f"food_enforcement_{filename_timestamp}.json"
    )

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(
            payload,
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path


def main() -> int:
    """Run the paginated extraction process."""

    load_dotenv(PROJECT_ROOT / ".env")

    print("Starting paginated openFDA recall extraction...")
    print(f"Endpoint: {BASE_URL}")
    print(f"Page size: {PAGE_LIMIT}")
    print(f"Maximum records requested: {MAX_RECORDS_TO_EXTRACT}")

    try:
        payload = fetch_recall_data_with_pagination()
        output_path = save_raw_response(payload)

    except RuntimeError as error:
        print(f"Extraction failed: {error}", file=sys.stderr)
        return 1

    records = payload["results"]
    metadata = payload.get("meta", {})
    total_available = metadata.get("results", {}).get(
        "total",
        "unknown",
    )

    print("\nExtraction completed successfully.")
    print(f"Records extracted: {len(records)}")
    print(f"Total records available: {total_available}")
    print(f"Raw file created: {output_path}")

    if records:
        first_record = records[0]
        last_record = records[-1]

        print("\nFirst record preview:")
        print(
            f"Recall number: "
            f"{first_record.get('recall_number')}"
        )
        print(
            f"Classification: "
            f"{first_record.get('classification')}"
        )
        print(
            f"Company: "
            f"{first_record.get('recalling_firm')}"
        )

        print("\nLast record preview:")
        print(
            f"Recall number: "
            f"{last_record.get('recall_number')}"
        )
        print(
            f"Classification: "
            f"{last_record.get('classification')}"
        )
        print(
            f"Company: "
            f"{last_record.get('recalling_firm')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())    