import json
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
PROMPT_PATH = PROJECT_ROOT / "prompts" / "recall_enrichment_prompt.md"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "pending_review_llm_payloads.jsonl"

load_dotenv(ENV_PATH)


def get_database_connection():
    """
    Create a PostgreSQL connection using environment variables from .env.
    """
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def load_prompt_template():
    """
    Load the LLM classification prompt from the prompts folder.
    """
    with open(PROMPT_PATH, "r", encoding="utf-8") as prompt_file:
        return prompt_file.read()


def fetch_records_needing_review(limit=10):
    """
    Fetch recall records that were marked for LLM/manual review.

    These are usually records where the rule-based classifier returned:
    - ai_category = 'Other'
    - needs_review = true
    - review_status = 'pending'
    """
    query = """
        SELECT
            recalls.recall_number,
            recalls.classification,
            recalls.product_description,
            recalls.reason_for_recall,
            enrichment.ai_category AS current_category,
            enrichment.hazard_type AS current_hazard_type,
            enrichment.hazard_name AS current_hazard_name,
            enrichment.ai_severity AS current_severity,
            enrichment.ai_confidence AS current_confidence,
            enrichment.review_status
        FROM ai_recall_enrichment AS enrichment
        INNER JOIN stg_fda_recalls AS recalls
            ON recalls.recall_number = enrichment.recall_number
        WHERE enrichment.needs_review = true
          AND enrichment.review_status = 'pending'
        ORDER BY recalls.recall_initiation_date DESC
        LIMIT %s;
    """

    with get_database_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (limit,))
            return cursor.fetchall()


def build_llm_payload(record):
    """
    Build the JSON object that would be sent to the LLM.
    """
    return {
        "recall_number": record["recall_number"],
        "classification": record["classification"],
        "product_description": record["product_description"],
        "reason_for_recall": record["reason_for_recall"],
    }


def export_payloads_to_jsonl(records, output_path):
    """
    Export LLM-ready payloads to a JSONL file.

    JSONL means each line is one valid JSON object.
    This format is useful for batch processing and future LLM workflows.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as output_file:
        for record in records:
            payload = build_llm_payload(record)
            output_file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main():
    print("LLM enrichment preview started.")
    print("This script does not call an LLM yet.")
    print()

    prompt_template = load_prompt_template()
    records = fetch_records_needing_review(limit=10)

    print(f"Prompt template loaded from: {PROMPT_PATH}")
    print(f"Prompt length: {len(prompt_template)} characters")
    print(f"Records needing review found: {len(records)}")
    print()

    if not records:
        print("No records currently need LLM review.")
        return

    export_payloads_to_jsonl(records, OUTPUT_PATH)

    print(f"LLM-ready payloads exported to: {OUTPUT_PATH}")
    print()

    for index, record in enumerate(records, start=1):
        payload = build_llm_payload(record)

        print("=" * 80)
        print(f"Record {index}: {record['recall_number']}")
        print("-" * 80)

        print("Current rule-based result:")
        print(
            json.dumps(
                {
                    "current_category": record["current_category"],
                    "current_hazard_type": record["current_hazard_type"],
                    "current_hazard_name": record["current_hazard_name"],
                    "current_severity": record["current_severity"],
                    "current_confidence": float(record["current_confidence"])
                    if record["current_confidence"] is not None
                    else None,
                    "review_status": record["review_status"],
                },
                indent=2,
            )
        )

        print()
        print("LLM input payload:")
        print(json.dumps(payload, indent=2))
        print()

    print("=" * 80)
    print("Preview complete.")
    print("Next phase will send these payloads to an LLM and store the response.")


if __name__ == "__main__":
    main()