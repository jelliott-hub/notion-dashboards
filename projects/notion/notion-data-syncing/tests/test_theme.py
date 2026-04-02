from core.theme import COLORS, plotly_template, echarts_theme


def test_colors_has_all_brand_colors():
    assert COLORS["navy"] == "#0D1B2A"
    assert COLORS["blue"] == "#2B7BE9"
    assert COLORS["blue_dark"] == "#1A5FC7"
    assert COLORS["blue_light"] == "#E8F1FD"
    assert COLORS["bg"] == "#F4F6FA"
    assert COLORS["white"] == "#FFFFFF"
    assert COLORS["border"] == "#E2E8F0"
    assert COLORS["slate"] == "#64748B"
    assert COLORS["success"] == "#22C55E"
    assert COLORS["warning"] == "#F59E0B"
    assert COLORS["error"] == "#E74C3C"


def test_plotly_template_is_valid():
    tpl = plotly_template()
    assert tpl.layout.paper_bgcolor == "#F4F6FA"
    assert tpl.layout.plot_bgcolor == "#FFFFFF"
    assert tpl.layout.font.color == "#0D1B2A"
    assert tpl.layout.colorway is not None
    assert len(tpl.layout.colorway) >= 5


def test_echarts_theme_has_required_keys():
    theme = echarts_theme()
    assert "color" in theme
    assert "backgroundColor" in theme
    assert theme["backgroundColor"] == "#FFFFFF"
