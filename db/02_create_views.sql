-- ============================================================
-- FDA Recall Intelligence Platform
-- Analytics view creation script
-- ============================================================


-- Main enriched recall view
CREATE OR REPLACE VIEW vw_recall_enriched AS
SELECT
    r.recall_number,
    r.event_id,
    r.status,
    r.classification,
    r.product_type,
    r.recalling_firm,
    r.product_description,
    r.reason_for_recall,
    r.product_quantity,
    r.city,
    r.state,
    r.country,
    r.recall_initiation_date,
    r.center_classification_date,
    r.report_date,
    r.termination_date,
    r.initial_firm_notification,
    r.voluntary_mandated,
    e.ai_category,
    e.hazard_type,
    e.hazard_name,
    e.ai_severity,
    e.ai_summary,
    e.ai_confidence,
    e.model_name,
    e.prompt_version,
    e.processed_at_utc AS enrichment_processed_at
FROM stg_fda_recalls r
LEFT JOIN ai_recall_enrichment e
    ON r.recall_number = e.recall_number;


-- Dashboard KPI summary
CREATE OR REPLACE VIEW vw_recall_kpi_summary AS
SELECT
    COUNT(*) AS total_recalls,
    COUNT(*) FILTER (WHERE ai_severity = 'Critical') AS critical_recalls,
    COUNT(*) FILTER (WHERE ai_severity = 'High') AS high_recalls,
    COUNT(*) FILTER (WHERE ai_severity = 'Medium') AS medium_recalls,
    COUNT(*) FILTER (WHERE ai_category = 'Other') AS other_recalls,
    COUNT(DISTINCT recalling_firm) AS unique_firms,
    COUNT(DISTINCT state) AS unique_states,
    COUNT(DISTINCT ai_category) AS unique_ai_categories,
    COUNT(DISTINCT hazard_name) AS unique_hazards
FROM vw_recall_enriched;


-- Category distribution
CREATE OR REPLACE VIEW vw_recall_category_summary AS
SELECT
    ai_category,
    COUNT(*) AS recall_count,
    ROUND(COUNT(*)::numeric * 100 / SUM(COUNT(*)) OVER (), 2) AS recall_percentage
FROM vw_recall_enriched
GROUP BY ai_category;


-- Severity distribution
CREATE OR REPLACE VIEW vw_recall_severity_summary AS
SELECT
    ai_severity,
    COUNT(*) AS recall_count,
    ROUND(COUNT(*)::numeric * 100 / SUM(COUNT(*)) OVER (), 2) AS recall_percentage
FROM vw_recall_enriched
GROUP BY ai_severity;


-- Hazard summary based on records with hazard_name populated
CREATE OR REPLACE VIEW vw_recall_hazard_summary AS
SELECT
    hazard_name,
    hazard_type,
    COUNT(*) AS recall_count,
    ROUND(COUNT(*)::numeric * 100 / SUM(COUNT(*)) OVER (), 2) AS recall_percentage
FROM vw_recall_enriched
WHERE hazard_name IS NOT NULL
GROUP BY hazard_name, hazard_type;


-- Hazard summary as percentage of all records
CREATE OR REPLACE VIEW vw_recall_hazard_summary_total_pct AS
SELECT
    hazard_name,
    hazard_type,
    COUNT(*) AS recall_count,
    ROUND(
        COUNT(*)::numeric * 100 / (SELECT COUNT(*) FROM vw_recall_enriched),
        2
    ) AS recall_percentage_of_total
FROM vw_recall_enriched
WHERE hazard_name IS NOT NULL
GROUP BY hazard_name, hazard_type;


-- State summary
CREATE OR REPLACE VIEW vw_recall_state_summary AS
SELECT
    state,
    COUNT(*) AS recall_count,
    ROUND(COUNT(*)::numeric * 100 / SUM(COUNT(*)) OVER (), 2) AS recall_percentage
FROM vw_recall_enriched
WHERE state IS NOT NULL
GROUP BY state;


-- Monthly trend summary
CREATE OR REPLACE VIEW vw_recall_monthly_trend AS
SELECT
    DATE_TRUNC('month', recall_initiation_date)::date AS recall_month,
    COUNT(*) AS recall_count,
    COUNT(*) FILTER (WHERE ai_severity = 'Critical') AS critical_count,
    COUNT(*) FILTER (WHERE ai_severity = 'High') AS high_count,
    COUNT(*) FILTER (WHERE ai_severity = 'Medium') AS medium_count
FROM vw_recall_enriched
WHERE recall_initiation_date IS NOT NULL
GROUP BY DATE_TRUNC('month', recall_initiation_date)::date;


-- Firm-level recall summary
CREATE OR REPLACE VIEW vw_recall_firm_summary AS
SELECT
    recalling_firm,
    COUNT(*) AS recall_count,
    COUNT(*) FILTER (WHERE ai_severity = 'Critical') AS critical_count,
    COUNT(*) FILTER (WHERE ai_severity = 'High') AS high_count,
    COUNT(*) FILTER (WHERE ai_severity = 'Medium') AS medium_count,
    COUNT(DISTINCT ai_category) AS category_count
FROM vw_recall_enriched
WHERE recalling_firm IS NOT NULL
GROUP BY recalling_firm;


-- State and category breakdown
CREATE OR REPLACE VIEW vw_recall_state_category_summary AS
SELECT
    state,
    ai_category,
    COUNT(*) AS recall_count
FROM vw_recall_enriched
WHERE state IS NOT NULL
GROUP BY state, ai_category;