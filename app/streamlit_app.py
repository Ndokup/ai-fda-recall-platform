import os
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv


st.set_page_config(
    page_title="FDA Recall Intelligence Platform",
    page_icon="🧠",
    layout="wide",
)

st.markdown(
    """
    <style>
    /* Main page background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #111827 45%, #020617 100%);
        color: #f8fafc;
    }

    /* Main content width and spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Dashboard title */
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 0.25rem;
    }

    .subtitle {
        font-size: 1.05rem;
        color: #cbd5e1;
        margin-bottom: 2rem;
    }

    /* Section headers */
    h2, h3 {
        color: #f8fafc;
    }

    /* KPI card style */
    .kpi-card {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 18px;
        padding: 1.2rem 1.4rem;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);
        min-height: 125px;
        transition: all 0.25s ease-in-out;
        cursor: pointer;
    }

    .kpi-card:hover {
        transform: translateY(-6px);
        border-color: rgba(96, 165, 250, 0.9);
        box-shadow: 0 18px 35px rgba(37, 99, 235, 0.35);
        background: rgba(30, 41, 59, 0.95);
    }

    .kpi-link {
        text-decoration: none !important;
        color: inherit !important;
    }

    .kpi-link:hover {
        text-decoration: none !important;
        color: inherit !important;
    }

    .kpi-label {
        color: #cbd5e1;
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }

    .kpi-value {
        color: #ffffff;
        font-size: 2.15rem;
        font-weight: 800;
        line-height: 1.1;
    }

    .kpi-note {
        color: #94a3b8;
        font-size: 0.8rem;
        margin-top: 0.35rem;
    }

    /* Insight banner */
    .insight-banner {
        background: linear-gradient(90deg, rgba(37,99,235,0.25), rgba(14,165,233,0.18));
        border: 1px solid rgba(96, 165, 250, 0.35);
        border-radius: 18px;
        padding: 1.2rem 1.4rem;
        margin: 1rem 0 2rem 0;
        color: #e0f2fe;
    }

    .insight-title {
        font-size: 1rem;
        font-weight: 700;
        color: #bfdbfe;
        margin-bottom: 0.25rem;
    }

    .insight-text {
        font-size: 1.15rem;
        font-weight: 600;
        color: #f8fafc;
    }

    /* Dataframe and chart containers */
    [data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
    }

    /* Divider spacing */
    hr {
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)


def get_database_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


@st.cache_data(ttl=300)
def run_query(query: str) -> pd.DataFrame:
    with get_database_connection() as connection:
        return pd.read_sql_query(query, connection)


st.markdown(
    """
    <div class="main-title">🧠 FDA Recall Intelligence Platform</div>
    <div class="subtitle">
        AI-ready food recall enrichment, hazard classification, and analytics dashboard built on PostgreSQL.
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Executive Summary")

kpi_df = run_query(
    """
    SELECT
        total_recalls,
        critical_recalls,
        high_recalls,
        medium_recalls,
        other_recalls,
        unique_firms,
        unique_states,
        unique_ai_categories,
        unique_hazards
    FROM vw_recall_kpi_summary;
    """
)

if kpi_df.empty:
    st.error("No KPI data found. Please check vw_recall_kpi_summary.")
    st.stop()

kpi = kpi_df.iloc[0]

critical_high_count = int(kpi["critical_recalls"]) + int(kpi["high_recalls"])
critical_high_pct = critical_high_count / int(kpi["total_recalls"]) * 100

st.markdown(
    f"""
    <div class="insight-banner">
        <div class="insight-title">Key Risk Insight</div>
        <div class="insight-text">
            {critical_high_count:,} of {int(kpi["total_recalls"]):,} recalls 
            ({critical_high_pct:.1f}%) were classified as High or Critical risk.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(
        f"""
        <a href="#explorer-section" class="kpi-link">
            <div class="kpi-card">
                <div class="kpi-label">Total Recalls</div>
                <div class="kpi-value">{int(kpi['total_recalls']):,}</div>
                <div class="kpi-note">Click to explore records</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <a href="#explorer-section" class="kpi-link">
            <div class="kpi-card">
                <div class="kpi-label">Critical Recalls</div>
                <div class="kpi-value">{int(kpi['critical_recalls']):,}</div>
                <div class="kpi-note">Click to filter in explorer</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <a href="#explorer-section" class="kpi-link">
            <div class="kpi-card">
                <div class="kpi-label">High Recalls</div>
                <div class="kpi-value">{int(kpi['high_recalls']):,}</div>
                <div class="kpi-note">High-risk recalls</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
        <a href="#explorer-section" class="kpi-link">
            <div class="kpi-card">
                <div class="kpi-label">Medium Recalls</div>
                <div class="kpi-value">{int(kpi['medium_recalls']):,}</div>
                <div class="kpi-note">Moderate risk</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with col5:
    st.markdown(
        f"""
        <a href="#explorer-section" class="kpi-link">
            <div class="kpi-card">
                <div class="kpi-label">Other Recalls</div>
                <div class="kpi-value">{int(kpi['other_recalls']):,}</div>
                <div class="kpi-note">Edge cases</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

st.write("")

col6, col7, col8, col9 = st.columns(4)

with col6:
    st.markdown(
        f"""
        <a href="#firm-section" class="kpi-link">
            <div class="kpi-card">
                <div class="kpi-label">Unique Firms</div>
                <div class="kpi-value">{int(kpi['unique_firms']):,}</div>
                <div class="kpi-note">Click to view firms</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with col7:
    st.markdown(
        f"""
        <a href="#state-section" class="kpi-link">
            <div class="kpi-card">
                <div class="kpi-label">Unique States</div>
                <div class="kpi-value">{int(kpi['unique_states']):,}</div>
                <div class="kpi-note">Click to view states</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with col8:
    st.markdown(
        f"""
        <a href="#category-section" class="kpi-link">
            <div class="kpi-card">
                <div class="kpi-label">AI Categories</div>
                <div class="kpi-value">{int(kpi['unique_ai_categories']):,}</div>
                <div class="kpi-note">Classification groups</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with col9:
    st.markdown(
        f"""
        <a href="#hazard-section" class="kpi-link">
            <div class="kpi-card">
                <div class="kpi-label">Unique Hazards</div>
                <div class="kpi-value">{int(kpi['unique_hazards']):,}</div>
                <div class="kpi-note">Detected hazards</div>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )


st.markdown('<div id="category-section"></div>', unsafe_allow_html=True)
st.divider()

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Recall Category Distribution")

    category_df = run_query(
        """
        SELECT
            ai_category,
            recall_count,
            recall_percentage
        FROM vw_recall_category_summary
        ORDER BY recall_count DESC;
        """
    )

    st.bar_chart(
        category_df,
        x="ai_category",
        y="recall_count",
    )

    st.dataframe(
        category_df,
        use_container_width=True,
        hide_index=True,
    )


with right_col:
    st.subheader("Severity Distribution")

    severity_df = run_query(
        """
        SELECT
            ai_severity,
            recall_count,
            recall_percentage
        FROM vw_recall_severity_summary
        ORDER BY
            CASE ai_severity
                WHEN 'Critical' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3
                WHEN 'Low' THEN 4
                ELSE 5
            END;
        """
    )

    st.bar_chart(
        severity_df,
        x="ai_severity",
        y="recall_count",
    )

    st.dataframe(
        severity_df,
        use_container_width=True,
        hide_index=True,
    )
st.markdown('<div id="hazard-section"></div>', unsafe_allow_html=True)
st.divider()

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Top 20 Hazards")

    hazard_df = run_query(
        """
        SELECT
            hazard_name,
            hazard_type,
            recall_count,
            recall_percentage_of_total
        FROM vw_recall_hazard_summary_total_pct
        ORDER BY recall_count DESC
        LIMIT 20;
        """
    )

    st.bar_chart(
        hazard_df,
        x="hazard_name",
        y="recall_count",
    )

    st.dataframe(
        hazard_df,
        use_container_width=True,
        hide_index=True,
    )


with right_col:
    st.subheader("Top 15 States")

    state_df = run_query(
        """
        SELECT
            state,
            recall_count,
            recall_percentage
        FROM vw_recall_state_summary
        ORDER BY recall_count DESC
        LIMIT 15;
        """
    )

    st.bar_chart(
        state_df,
        x="state",
        y="recall_count",
    )

    st.dataframe(
        state_df,
        use_container_width=True,
        hide_index=True,
    )
st.markdown('<div id="trend-section"></div>', unsafe_allow_html=True)
st.divider()

st.subheader("Monthly Recall Trend")

monthly_df = run_query(
    """
    SELECT
        recall_month,
        recall_count,
        critical_count,
        high_count,
        medium_count
    FROM vw_recall_monthly_trend
    ORDER BY recall_month;
    """
)

st.line_chart(
    monthly_df,
    x="recall_month",
    y=["recall_count", "critical_count", "high_count", "medium_count"],
)

st.dataframe(
    monthly_df.tail(20),
    use_container_width=True,
    hide_index=True,
)

st.markdown('<div id="firm-section"></div>', unsafe_allow_html=True)
st.divider()

st.subheader("Top Recalling Firms")

firm_df = run_query(
    """
    SELECT
        recalling_firm,
        recall_count,
        critical_count,
        high_count,
        medium_count,
        category_count
    FROM vw_recall_firm_summary
    ORDER BY recall_count DESC
    LIMIT 25;
    """
)

st.dataframe(
    firm_df,
    use_container_width=True,
    hide_index=True,
) 

st.markdown('<div id="explorer-section"></div>', unsafe_allow_html=True)
st.divider()

st.subheader("Recall Record Explorer")

recall_df = run_query(
    """
    SELECT
        recall_number,
        recall_initiation_date,
        state,
        classification,
        ai_category,
        hazard_type,
        hazard_name,
        ai_severity,
        recalling_firm,
        product_description,
        reason_for_recall
    FROM vw_recall_enriched
    ORDER BY recall_initiation_date DESC;
    """
)

filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    selected_categories = st.multiselect(
        "Filter by AI Category",
        options=sorted(recall_df["ai_category"].dropna().unique()),
        default=[],
    )

with filter_col2:
    selected_severities = st.multiselect(
        "Filter by Severity",
        options=["Critical", "High", "Medium", "Low"],
        default=[],
    )

with filter_col3:
    selected_states = st.multiselect(
        "Filter by State",
        options=sorted(recall_df["state"].dropna().unique()),
        default=[],
    )

search_text = st.text_input(
    "Search product, firm, reason, or recall number",
    placeholder="Example: Listeria, milk, F-1453-2017, California firm...",
)

filtered_df = recall_df.copy()

if selected_categories:
    filtered_df = filtered_df[filtered_df["ai_category"].isin(selected_categories)]

if selected_severities:
    filtered_df = filtered_df[filtered_df["ai_severity"].isin(selected_severities)]

if selected_states:
    filtered_df = filtered_df[filtered_df["state"].isin(selected_states)]

if search_text:
    search_text_lower = search_text.lower()

    filtered_df = filtered_df[
        filtered_df["recall_number"].fillna("").str.lower().str.contains(search_text_lower)
        | filtered_df["recalling_firm"].fillna("").str.lower().str.contains(search_text_lower)
        | filtered_df["product_description"].fillna("").str.lower().str.contains(search_text_lower)
        | filtered_df["reason_for_recall"].fillna("").str.lower().str.contains(search_text_lower)
        | filtered_df["hazard_name"].fillna("").str.lower().str.contains(search_text_lower)
    ]

st.write(f"Showing {len(filtered_df):,} of {len(recall_df):,} recall records")

st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True,
)