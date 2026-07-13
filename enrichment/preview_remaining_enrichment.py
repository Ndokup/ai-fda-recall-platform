from pathlib import Path
import csv

from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from datetime import datetime

from rule_based_enrichment import (
    get_database_connection,
    classify_recall,
)


BATCH_SIZE = 1000

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"


OUTPUT_FILE = OUTPUT_DIR / f"remaining_enrichment_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def fetch_remaining_records(connection):
    """
    Fetch records from staging that are not yet present in ai_recall_enrichment.

    This does not modify data.
    It only selects records that still need enrichment.
    """

    query = """
        SELECT
            recall_number,
            classification,
            product_description,
            reason_for_recall
        FROM stg_fda_recalls AS recalls
        WHERE NOT EXISTS (
            SELECT 1
            FROM ai_recall_enrichment AS enrichment
            WHERE enrichment.recall_number = recalls.recall_number
        )
        ORDER BY recall_initiation_date DESC
        LIMIT %s;
    """

    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, (BATCH_SIZE,))
        return cursor.fetchall()


def write_preview_csv(preview_rows):
    """
    Save preview output to a CSV file so we can inspect it later.
    This is useful because terminal output can be hard to read for hundreds of rows.
    """

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "recall_number",
        "classification",
        "ai_category",
        "hazard_type",
        "hazard_name",
        "ai_severity",
        "ai_confidence",
        "product_description",
        "reason_for_recall",
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(preview_rows)


def main():
    load_dotenv()

    category_counts = {}
    severity_counts = {}
    other_rows = []
    preview_rows = []

    with get_database_connection() as connection:
        records = fetch_remaining_records(connection)

        print(f"Remaining records selected for preview: {len(records)}")
        print("Preview mode only. No database changes will be made.")

        if not records:
            print("No remaining records found.")
            return

        for record in records:
            enrichment = classify_recall(
                product_description=record["product_description"],
                reason_for_recall=record["reason_for_recall"],
                classification=record["classification"],
            )

            ai_category = enrichment["ai_category"]
            ai_severity = enrichment["ai_severity"]

            category_counts[ai_category] = category_counts.get(ai_category, 0) + 1
            severity_counts[ai_severity] = severity_counts.get(ai_severity, 0) + 1

            preview_row = {
                "recall_number": record["recall_number"],
                "classification": record["classification"],
                "ai_category": enrichment["ai_category"],
                "hazard_type": enrichment["hazard_type"],
                "hazard_name": enrichment["hazard_name"],
                "ai_severity": enrichment["ai_severity"],
                "ai_confidence": enrichment["ai_confidence"],
                "product_description": record["product_description"],
                "reason_for_recall": record["reason_for_recall"],
            }

            preview_rows.append(preview_row)

            if ai_category == "Other":
                other_rows.append(preview_row)

        write_preview_csv(preview_rows)

        print("\nBatch category summary:")
        for category, count in sorted(
            category_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            print(f"{category}: {count}")

        print("\nBatch severity summary:")
        for severity, count in sorted(
            severity_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            print(f"{severity}: {count}")

        print("\nOther rows:")
        print(f"Other count: {len(other_rows)}")

        if other_rows:
            for row in other_rows:
                print("\n" + "-" * 80)
                print(f"Recall Number: {row['recall_number']}")
                print(f"FDA Classification: {row['classification']}")
                print(f"Product: {row['product_description']}")
                print(f"Reason: {row['reason_for_recall']}")
        else:
            print("No Other rows found.")

        print(f"\nPreview CSV created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()