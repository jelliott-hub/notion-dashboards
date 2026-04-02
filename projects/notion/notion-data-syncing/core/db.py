"""Supabase connection and cached query functions for notion_sync views."""

import re
import pandas as pd

# Valid view name pattern — alphanumeric + underscores only
_VIEW_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# All known notion_sync views
VIEWS = {
    # Finance
    "finance_close_dashboard",
    "finance_pnl",
    "finance_ar_aging",
    "finance_variance",
    "finance_accounting_inbox",
    # Sales
    "sales_rfp_pipeline",
    "sales_deals",
    "sales_opportunities",
    "sales_prospects",
    "sales_state_profiles",
    "sales_inbox",
    # Support
    "calls_weekly",
    "calls_by_agent",
    "calls_by_topic",
    "calls_log",
    "tickets_log",
    "tickets_monthly",
}


def _get_connection():
    """Get or create the Supabase Postgres connection."""
    import streamlit as st
    return st.connection("supabase", type="sql")


def query_view(view_name: str, ttl: int = 300) -> pd.DataFrame:
    """
    Query a notion_sync view and return a cached DataFrame.

    Args:
        view_name: Name of the view in notion_sync schema (e.g., "finance_pnl")
        ttl: Cache time-to-live in seconds (default 5 minutes)

    Returns:
        pd.DataFrame with the query results
    """
    if not _VIEW_NAME_RE.match(view_name):
        raise ValueError(f"Invalid view name: {view_name!r}")

    return _execute_query(view_name, ttl)


def _execute_query(view_name: str, ttl: int) -> pd.DataFrame:
    """Execute query against notion_sync schema, using st.cache_data when available."""
    try:
        import streamlit as st
        # Only use the cached variant if a Streamlit runtime is active
        st.runtime.exists()  # raises RuntimeError outside Streamlit
        return _cached_query(view_name, ttl)
    except (AttributeError, Exception):
        # Outside Streamlit runtime (e.g., in tests) — run uncached
        return _run_query(view_name, ttl)


def _run_query(view_name: str, ttl: int) -> pd.DataFrame:
    """Uncached query execution — used in tests and non-Streamlit contexts."""
    conn = _get_connection()
    return conn.query(f"SELECT * FROM notion_sync.{view_name}", ttl=ttl)


def _make_cached_query():
    """Build the @st.cache_data-wrapped query function only when Streamlit is available."""
    try:
        import streamlit as st

        @st.cache_data(ttl=300, show_spinner=False)
        def _cached(view_name: str, _ttl: int) -> pd.DataFrame:
            """Cached query execution. The _ttl param is prefixed with _ so Streamlit
            doesn't hash it (the decorator's ttl handles caching)."""
            conn = _get_connection()
            return conn.query(f"SELECT * FROM notion_sync.{view_name}", ttl=_ttl)

        return _cached
    except ImportError:
        return None


_cached_query = _make_cached_query()
