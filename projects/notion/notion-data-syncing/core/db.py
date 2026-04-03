"""Supabase connection via REST API (HTTPS) for notion_sync views."""

import re
import requests
import streamlit as st
import pandas as pd

_VIEW_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

SUPABASE_URL = "https://dozjdswqnzqwvieqvwpe.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRvempkc3dxbnpxd3ZpZXF2d3BlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2MDg4NTIsImV4cCI6MjA4ODE4NDg1Mn0.encWfQXeN1u233MiwZpqD3_iaX9T0g9ybQtWRagWMfg"


def query_view(view_name: str, ttl: int = 300) -> pd.DataFrame:
    """
    Query a notion_sync view via Supabase REST API and return a cached DataFrame.

    Args:
        view_name: Name of the view in notion_sync schema (e.g., "finance_pnl")
        ttl: Cache time-to-live in seconds (default 5 minutes)

    Returns:
        pd.DataFrame with the query results
    """
    if not _VIEW_NAME_RE.match(view_name):
        raise ValueError(f"Invalid view name: {view_name!r}")

    try:
        st.runtime.exists()
        return _cached_query(view_name, ttl)
    except Exception:
        return _fetch_view(view_name)


@st.cache_data(ttl=300, show_spinner="Loading data...")
def _cached_query(view_name: str, _ttl: int) -> pd.DataFrame:
    return _fetch_view(view_name)


def _fetch_view(view_name: str) -> pd.DataFrame:
    """Fetch all rows from a notion_sync view via Supabase REST API."""
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Accept": "application/json",
        "Accept-Profile": "notion_sync",
    }

    # Supabase REST API paginates at 1000 rows by default.
    # Fetch with a high limit to get all rows in one request.
    url = f"{SUPABASE_URL}/rest/v1/{view_name}?limit=10000"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    if not data:
        return pd.DataFrame()

    return pd.DataFrame(data)
