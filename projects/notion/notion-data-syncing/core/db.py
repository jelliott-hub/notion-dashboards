"""
Supabase REST API query layer for Streamlit dashboards.

Queries any Supabase schema via the PostgREST API and returns cached
DataFrames with automatic type coercion (strings → numeric/datetime/bool).

Usage::

    from core.db import query_view

    # Default schema (notion_sync)
    df = query_view("finance_pnl")

    # Explicit schema
    df = query_view("mv_call_spine", schema="analytics")

    # Custom views in any schema
    df = query_view("dim_customer", schema="analytics")

The returned DataFrame has types coerced automatically:
- Column names ending in _date, _month, _at, _week, _start → datetime
- String columns that look numeric → float/int
- String columns with only true/false → bool
"""

import re
import requests
import streamlit as st
import pandas as pd

_VIEW_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

_DEFAULT_URL = "https://dozjdswqnzqwvieqvwpe.supabase.co"
_DEFAULT_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRvempkc3dxbnpxd3ZpZXF2d3BlIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzI2MDg4NTIsImV4cCI6MjA4ODE4NDg1Mn0."
    "encWfQXeN1u233MiwZpqD3_iaX9T0g9ybQtWRagWMfg"
)

CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_supabase_url() -> str:
    return st.secrets.get("supabase", {}).get("url", _DEFAULT_URL)


def _get_supabase_key() -> str:
    return st.secrets.get("supabase", {}).get("anon_key", _DEFAULT_ANON_KEY)


def query_view(view_name: str, schema: str = "notion_sync") -> pd.DataFrame:
    """
    Query a Supabase view/table and return a cached, type-coerced DataFrame.

    Args:
        view_name: Name of the view or table (e.g., "finance_pnl", "mv_call_spine").
                   Must be lowercase alphanumeric + underscores.
        schema: Supabase schema to query. Default "notion_sync".
                Common schemas: "notion_sync", "analytics", "public".

    Returns:
        pd.DataFrame with automatic type coercion applied.
        Returns empty DataFrame if the view has no rows.

    Raises:
        ValueError: If view_name contains invalid characters.
        requests.HTTPError: If the Supabase API returns an error (e.g., 404 for
                           missing view, 403 for unauthorized schema).

    Example::

        df = query_view("finance_pnl")
        df = query_view("mv_call_spine", schema="analytics")
    """
    if not _VIEW_NAME_RE.match(view_name):
        raise ValueError(f"Invalid view name: {view_name!r}")

    try:
        st.runtime.exists()
        return _cached_query(view_name, schema)
    except Exception:
        return _fetch_view(view_name, schema)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Loading data...")
def _cached_query(view_name: str, schema: str) -> pd.DataFrame:
    return _fetch_view(view_name, schema)


def _fetch_view(view_name: str, schema: str = "notion_sync") -> pd.DataFrame:
    """Fetch all rows from a Supabase view via REST API."""
    headers = {
        "apikey": _get_supabase_key(),
        "Accept": "application/json",
        "Accept-Profile": schema,
    }

    url = f"{_get_supabase_url()}/rest/v1/{view_name}?limit=10000"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    return _coerce_types(df)


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Auto-coerce REST API string values to proper pandas types.

    Applied automatically by query_view — new tabs should NOT need
    manual pd.to_numeric / pd.to_datetime calls.

    Rules:
        - Columns ending in _date, _month, _at, _week, _start → datetime
        - String columns where >=50% of values parse as numbers → numeric
        - String columns with only true/false values → bool
        - Everything else stays as-is
    """
    for col in df.columns:
        if df[col].dropna().empty:
            continue

        sample = df[col].dropna().iloc[0]

        if not isinstance(sample, str):
            continue

        # Datetime columns by name convention
        if any(col.endswith(s) for s in ("_date", "_month", "_at", "_week", "_start")):
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
                continue
            except Exception:
                pass

        # Numeric conversion
        try:
            converted = pd.to_numeric(df[col], errors="coerce")
            if converted.notna().sum() >= df[col].notna().sum() * 0.5:
                df[col] = converted
                continue
        except Exception:
            pass

        # Boolean conversion
        if set(df[col].dropna().unique()) <= {"true", "false", "True", "False"}:
            df[col] = df[col].map({"true": True, "false": False, "True": True, "False": False})

    return df
