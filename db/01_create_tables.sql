-- ============================================================
-- FDA Recall Intelligence Platform
-- Table creation script
-- ============================================================

-- Staging table for cleaned FDA recall records
CREATE TABLE IF NOT EXISTS stg_fda_recalls (
    recall_number TEXT PRIMARY KEY,
    event_id TEXT,
    status TEXT,
    classification TEXT,
    product_type TEXT,
    recalling_firm TEXT,
    product_description TEXT,
    reason_for_recall TEXT,
    product_quantity TEXT,
    code_info TEXT,
    distribution_pattern TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT,
    recall_initiation_date DATE,
    center_classification_date DATE,
    report_date DATE,
    termination_date DATE,
    initial_firm_notification TEXT,
    voluntary_mandated TEXT,
    source_file TEXT,
    processed_at_utc TIMESTAMP
);


-- AI-ready enrichment output table
CREATE TABLE IF NOT EXISTS ai_recall_enrichment (
    recall_number TEXT PRIMARY KEY,
    ai_category TEXT NOT NULL,
    hazard_type TEXT NOT NULL,
    hazard_name TEXT,
    ai_severity TEXT NOT NULL,
    ai_summary TEXT NOT NULL,
    ai_confidence NUMERIC(4, 3),
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    processed_at_utc TIMESTAMP NOT NULL,
    raw_ai_response JSONB,

    CONSTRAINT fk_ai_recall_number
        FOREIGN KEY (recall_number)
        REFERENCES stg_fda_recalls (recall_number),

    CONSTRAINT chk_ai_category
        CHECK (
            ai_category IN (
                'Undeclared allergen',
                'Pathogen contamination',
                'Foreign material contamination',
                'Chemical contamination',
                'Mislabeling or packaging error',
                'Quality or manufacturing issue',
                'Temperature or storage issue',
                'Product mix-up',
                'Other'
            )
        ),

    CONSTRAINT chk_hazard_type
        CHECK (
            hazard_type IN (
                'Allergen',
                'Pathogen',
                'Foreign Material',
                'Chemical',
                'Labeling',
                'Quality',
                'Temperature',
                'Product Mix-up',
                'Unknown'
            )
        ),

    CONSTRAINT chk_ai_severity
        CHECK (
            ai_severity IN ('Low', 'Medium', 'High', 'Critical')
        ),

    CONSTRAINT chk_ai_confidence
        CHECK (
            ai_confidence IS NULL
            OR (ai_confidence >= 0 AND ai_confidence <= 1)
        )
);