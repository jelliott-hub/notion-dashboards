import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


@patch("core.db._get_supabase_key", return_value="test-key")
@patch("core.db._get_supabase_url", return_value="https://test.supabase.co")
def test_fetch_view_returns_dataframe(mock_url, mock_key):
    """_fetch_view should return a pandas DataFrame."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = [{"col": 1}, {"col": 2}, {"col": 3}]
    mock_resp.raise_for_status = MagicMock()

    with patch("core.db.requests.get", return_value=mock_resp):
        from core.db import _fetch_view

        result = _fetch_view("finance_close_dashboard")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3


@patch("core.db._get_supabase_key", return_value="test-key")
@patch("core.db._get_supabase_url", return_value="https://test.supabase.co")
def test_fetch_view_uses_correct_schema(mock_url, mock_key):
    """_fetch_view should pass the schema as Accept-Profile header."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = []
    mock_resp.raise_for_status = MagicMock()

    with patch("core.db.requests.get", return_value=mock_resp) as mock_get:
        from core.db import _fetch_view

        _fetch_view("finance_pnl")
        headers = mock_get.call_args[1].get("headers", {})
        assert headers["Accept-Profile"] == "notion_sync"

        _fetch_view("mv_call_spine", schema="analytics")
        headers = mock_get.call_args[1].get("headers", {})
        assert headers["Accept-Profile"] == "analytics"


def test_query_view_rejects_dangerous_names():
    """query_view should reject view names with SQL injection attempts."""
    from core.db import query_view

    with pytest.raises(ValueError):
        query_view("finance_pnl; DROP TABLE users")

    with pytest.raises(ValueError):
        query_view("finance_pnl--comment")


@patch("core.db._get_supabase_key", return_value="test-key")
@patch("core.db._get_supabase_url", return_value="https://test.supabase.co")
def test_coerce_types_converts_dates(mock_url, mock_key):
    """_coerce_types should convert date-named string columns to datetime."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {"report_month": "2026-01-01", "name": "Test"},
        {"report_month": "2026-02-01", "name": "Test2"},
    ]
    mock_resp.raise_for_status = MagicMock()

    with patch("core.db.requests.get", return_value=mock_resp):
        from core.db import _fetch_view

        df = _fetch_view("test_view")
        assert pd.api.types.is_datetime64_any_dtype(df["report_month"])
        assert pd.api.types.is_string_dtype(df["name"])  # stays as string


@patch("core.db._get_supabase_key", return_value="test-key")
@patch("core.db._get_supabase_url", return_value="https://test.supabase.co")
def test_coerce_types_converts_booleans(mock_url, mock_key):
    """_coerce_types should convert true/false strings to bool."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {"is_active": "true", "name": "A"},
        {"is_active": "false", "name": "B"},
    ]
    mock_resp.raise_for_status = MagicMock()

    with patch("core.db.requests.get", return_value=mock_resp):
        from core.db import _fetch_view

        df = _fetch_view("test_view")
        assert df["is_active"].dtype == bool
        assert bool(df["is_active"].iloc[0]) is True
