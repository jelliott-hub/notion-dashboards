import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


def test_query_view_returns_dataframe():
    """query_view should return a pandas DataFrame."""
    mock_conn = MagicMock()
    mock_conn.query.return_value = pd.DataFrame({"col": [1, 2, 3]})

    with patch("core.db._get_connection", return_value=mock_conn):
        from core.db import query_view

        result = query_view("finance_close_dashboard")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3


def test_query_view_builds_correct_sql():
    """query_view should query notion_sync.<view_name>."""
    mock_conn = MagicMock()
    mock_conn.query.return_value = pd.DataFrame()

    with patch("core.db._get_connection", return_value=mock_conn):
        from core.db import query_view

        query_view("finance_pnl")
        call_args = mock_conn.query.call_args
        assert "notion_sync.finance_pnl" in call_args[0][0]


def test_query_view_rejects_dangerous_names():
    """query_view should reject view names with SQL injection attempts."""
    from core.db import query_view

    with pytest.raises(ValueError):
        query_view("finance_pnl; DROP TABLE users")

    with pytest.raises(ValueError):
        query_view("finance_pnl--comment")
