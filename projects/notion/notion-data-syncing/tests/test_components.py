from core.components import kpi_strip_html, detail_panel_html, status_pill_html


def test_kpi_strip_html_renders_all_items():
    items = [
        {"label": "Revenue", "value": "$412K", "color": "#0D1B2A"},
        {"label": "Margin", "value": "62.4%", "color": "#22C55E"},
    ]
    html = kpi_strip_html(items)
    assert "Revenue" in html
    assert "$412K" in html
    assert "Margin" in html
    assert "62.4%" in html
    assert "#22C55E" in html


def test_kpi_strip_html_handles_subtitle():
    items = [{"label": "Test", "value": "123", "color": "#000", "subtitle": "extra info"}]
    html = kpi_strip_html(items)
    assert "extra info" in html


def test_detail_panel_html_renders_fields():
    fields = {"GL Code": "4110", "GL Name": "Support Revenue", "Delta": "$530"}
    html = detail_panel_html("4110 Support Revenue", fields)
    assert "4110 Support Revenue" in html
    assert "GL Code" in html
    assert "Support Revenue" in html
    assert "$530" in html


def test_status_pill_html_applies_correct_colors():
    html = status_pill_html("PASS", "success")
    assert "#22C55E" in html
    assert "PASS" in html

    html = status_pill_html("FAIL", "error")
    assert "#E74C3C" in html

    html = status_pill_html("WARN", "warning")
    assert "#F59E0B" in html
