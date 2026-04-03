import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


def test_query_view_returns_dataframe():
    """query_view should return a pandas DataFrame."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = [{"col": 1}, {"col": 2}, {"col": 3}]
    mock_resp.raise_for_status = MagicMock()

    with patch("core.db.requests.get", return_value=mock_resp), \
         patch("core.db.st.runtime"):
        from core.db import _fetch_view

        result = _fetch_view("finance_close_dashboard")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3


def test_query_view_calls_correct_url():
    """query_view should hit the notion_sync REST endpoint."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = []
    mock_resp.raise_for_status = MagicMock()

    with patch("core.db.requests.get", return_value=mock_resp) as mock_get:
        from core.db import _fetch_view

        _fetch_view("finance_pnl")
        call_url = mock_get.call_args[0][0]
        assert "finance_pnl" in call_url
        call_headers = mock_get.call_args[1].get("headers", mock_get.call_args[0][1] if len(mock_get.call_args[0]) > 1 else {})
        if not call_headers:
            call_headers = mock_get.call_args[1].get("headers", {})
        assert call_headers.get("Accept-Profile") == "notion_sync"


def test_query_view_rejects_dangerous_names():
    """query_view should reject view names with SQL injection attempts."""
    from core.db import query_view

    with pytest.raises(ValueError):
        query_view("finance_pnl; DROP TABLE users")

    with pytest.raises(ValueError):
        query_view("finance_pnl--comment")
