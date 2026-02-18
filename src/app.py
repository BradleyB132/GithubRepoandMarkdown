"""
Streamlit UI for quickly exploring consolidated production data.

This application reads authoritative data from the project's PostgreSQL
database (Render) and does NOT allow file uploads. The UI automatically
loads data from the DB on page load and provides sidebar filters. Data is
cached so widget interactions (filters) do not re-run DB queries and
restart the page.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any

try:
    from src.consolidator import consolidate
    from src.report import summary_metrics, high_severity_shipped
    from src.db import get_engine, fetch_source_rows
except Exception:
    # Fallback when run as a script (streamlit run src/app.py)
    from consolidator import consolidate
    from report import summary_metrics, high_severity_shipped
    from db import get_engine, fetch_source_rows


# Cache DB loads so that filters and widget interactions do not re-run
# expensive DB calls on every widget change. TTL is 300 seconds by default.
@st.cache_data(ttl=300)
def load_db_data_cached():
    """Return (production_rows, quality_rows, shipping_rows) loaded from DB.

    Raises exceptions up to caller so the UI can display messages.
    """
    engine = get_engine()
    return fetch_source_rows(engine)


def main() -> None:
    st.title("Lot Consolidation & Reporting")
    st.markdown("Data is loaded from the configured database; use sidebar filters to refine the view.")

    # Load data (cached). Failures are shown but do not crash the UI.
    prod_rows: List[Dict[str, Any]] = []
    qual_rows: List[Dict[str, Any]] = []
    ship_rows: List[Dict[str, Any]] = []
    try:
        prod_rows, qual_rows, ship_rows = load_db_data_cached()
        st.success(f"Loaded {len(prod_rows)} production rows, {len(qual_rows)} quality rows, {len(ship_rows)} shipping rows from DB.")
    except Exception as exc:
        st.error(f"Failed to load data from DB: {exc}")

    # Consolidate immediately so filters can act on the consolidated set
    consolidated, flags = consolidate(prod_rows, qual_rows, ship_rows)

    st.write("### Consolidated Records")
    if consolidated:
        df_con = pd.DataFrame(consolidated)
        if "Production_Date" in df_con.columns:
            df_con["Production_Date"] = pd.to_datetime(df_con["Production_Date"], errors="coerce")

        # Sidebar filters
        st.sidebar.header("Filters")
        line_options = sorted({str(x) for x in df_con.get("Line_No", []).tolist() if x is not None})
        if not line_options:
            line_options = ["Unknown"]
        # Preserve selections across reruns using session_state keys
        if "selected_lines" not in st.session_state:
            st.session_state.selected_lines = line_options
        selected_lines = st.sidebar.multiselect("Production lines", options=line_options, default=st.session_state.selected_lines, key="selected_lines")

        if "Production_Date" in df_con.columns and not df_con["Production_Date"].isna().all():
            min_date = df_con["Production_Date"].min().date()
            max_date = df_con["Production_Date"].max().date()
            # Use a stable key to preserve date selection between reruns
            if "production_date_range" not in st.session_state:
                st.session_state.production_date_range = (min_date, max_date)
            date_val = st.sidebar.date_input("Production date range", value=st.session_state.production_date_range, key="production_date_range")
            if isinstance(date_val, tuple) and len(date_val) == 2:
                start_date, end_date = date_val
            else:
                start_date = date_val
                end_date = date_val
        else:
            start_date = None
            end_date = None

        severity_set = set()
        defect_set = set()
        for lst in df_con.get("Severities", []).tolist():
            if isinstance(lst, list):
                severity_set.update([str(x) for x in lst if x])
        for lst in df_con.get("Defect_Types", []).tolist():
            if isinstance(lst, list):
                defect_set.update([str(x) for x in lst if x])

        if "selected_severities" not in st.session_state:
            st.session_state.selected_severities = sorted(severity_set)
        if "selected_defects" not in st.session_state:
            st.session_state.selected_defects = sorted(defect_set)
        if "shipped_choice" not in st.session_state:
            st.session_state.shipped_choice = "All"

        selected_severities = st.sidebar.multiselect("Defect severities", options=sorted(severity_set), default=st.session_state.selected_severities, key="selected_severities")
        selected_defects = st.sidebar.multiselect("Defect types", options=sorted(defect_set), default=st.session_state.selected_defects, key="selected_defects")
        shipped_choice = st.sidebar.selectbox("Shipped status", options=["All", "Shipped", "Not Shipped"], index=["All", "Shipped", "Not Shipped"].index(st.session_state.shipped_choice), key="shipped_choice")

        # Apply filters
        mask = pd.Series(True, index=df_con.index)
        if selected_lines:
            mask &= df_con.get("Line_No", pd.Series([None]*len(df_con))).astype(str).isin(selected_lines)
        if start_date and end_date and "Production_Date" in df_con.columns:
            mask &= df_con["Production_Date"].apply(lambda d: (d is not pd.NaT) and (start_date <= d.date() <= end_date))

        if selected_severities:
            def sev_match(x):
                if not x:
                    return False
                if isinstance(x, list):
                    return any(str(s) in selected_severities for s in x)
                return any(str(s) in selected_severities for s in [x])

            mask &= df_con.get("Severities", pd.Series([[]]*len(df_con))).apply(sev_match)

        if selected_defects:
            def defect_match(x):
                if not x:
                    return False
                if isinstance(x, list):
                    return any(str(s) in selected_defects for s in x)
                return any(str(s) in selected_defects for s in [x])

            mask &= df_con.get("Defect_Types", pd.Series([[]]*len(df_con))).apply(defect_match)

        def shipped_flag(s):
            if not isinstance(s, dict):
                return False
            return bool(s.get("is_shipped") or s.get("Is_Shipped") or s.get("isShipped"))

        if shipped_choice == "Shipped":
            mask &= df_con.get("Shipping", pd.Series([None]*len(df_con))).apply(shipped_flag)
        elif shipped_choice == "Not Shipped":
            mask &= ~df_con.get("Shipping", pd.Series([None]*len(df_con))).apply(shipped_flag)

        df_display = df_con[mask].copy()
        for col in ("Inspections", "Shipping", "Defect_Types", "Severities"):
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(lambda v: str(v))

        st.dataframe(df_display)
    else:
        st.info("No consolidated records to display.")

    st.write("### Flags for Review")
    if flags:
        df_flags = pd.DataFrame(flags)
        st.dataframe(df_flags)
    else:
        st.info("No flags detected.")

    metrics = summary_metrics(consolidated)
    st.write("### Summary Metrics")
    top_lines = metrics.get("top_lines", [])
    if top_lines:
        df_top = pd.DataFrame(top_lines)
        st.subheader("Top lines by defects")
        st.dataframe(df_top)

    trending = metrics.get("trending_defects", [])
    if trending:
        df_trend = pd.DataFrame(trending, columns=["defect_type", "count"])
        st.subheader("Trending defect types")
        st.dataframe(df_trend)

    shipped_lots = metrics.get("shipped_lots", [])
    if shipped_lots:
        df_shipped = pd.DataFrame(shipped_lots)
        st.subheader("Shipped lots")
        st.dataframe(df_shipped)

    st.write("### High Severity Defects Already Shipped")
    high = high_severity_shipped(consolidated)
    if high:
        df_high = pd.DataFrame(high)
        if "Shipping" in df_high.columns:
            df_high["Shipping"] = df_high["Shipping"].apply(lambda v: str(v))
        st.dataframe(df_high)
    else:
        st.info("No high-severity defects found that have shipped.")


if __name__ == "__main__":
    main()
