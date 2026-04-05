"""Revenue — Stripe-inspired bento dashboard.

Single-page, chromeless layout covering revenue trends, volume,
retention cohorts, and concentration risk.
Run with: streamlit run apps/revenue/app.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from core.db import query_view
from core.style import (
    inject_css, metric_card, card_header, section_label,
    page_header, chart_layout, CHART_COLORS, PALETTE,
)

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(page_title="Revenue", page_icon="◆", layout="wide")
inject_css()
st.html(page_header("Revenue", "P&L, volume, retention & concentration"))


# ── Data ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load():
    return {
        "decomp": query_view("revenue_decomposition"),
        "volume": query_view("revenue_volume_monthly"),
        "vol_weekly": query_view("volume_weekly"),
        "unit_econ": query_view("unit_economics_monthly"),
        "retention": query_view("revenue_retention_summary"),
        "conc_trend": query_view("customer_concentration_trend"),
        "conc_customers": query_view("customer_concentration_top"),
    }


data = load()
decomp = data["decomp"].copy()
volume = data["volume"].copy()
vol_weekly = data["vol_weekly"].copy()
unit_econ = data["unit_econ"].copy()
retention = data["retention"].copy()
conc_trend = data["conc_trend"].copy()
conc_cust = data["conc_customers"].copy()


# ── Type coercion ────────────────────────────────────────────────────

def _num(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

def _dt(df, col):
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")


_dt(decomp, "report_month")
_num(decomp, [
    "gross_revenue", "net_revenue", "passthrough_revenue",
    "gross_mom_pct", "gross_yoy_pct", "net_mom_pct",
    "expansion_dollars", "contraction_dollars", "new_dollars", "churned_dollars",
    "new_customers", "churned_customers", "expansion_customers", "contraction_customers",
    "stable_customers",
])

_dt(volume, "report_month")
_num(volume, ["volume", "gross_revenue", "processing_fee", "gov_fee",
              "avg_fee_per_scan", "active_customers"])

_dt(vol_weekly, "period_start")
_dt(vol_weekly, "report_month")
_num(vol_weekly, ["volume", "processing_fee", "gov_fee", "sam_fee", "gross_revenue"])

_dt(unit_econ, "report_month")
_num(unit_econ, ["volume", "processing_fee", "gov_fee", "sam_fee", "gross_revenue",
                 "processing_per_scan", "gov_per_scan", "sam_per_scan", "gross_per_scan"])

_dt(retention, "evaluation_month")
_num(retention, ["customer_count", "monthly_revenue", "ttm_current", "ttm_prior", "ttm_delta"])

_dt(conc_trend, "evaluation_month")
_num(conc_trend, ["hhi_index", "top1_share_pct", "top5_share_pct", "top10_share_pct",
                  "top20_share_pct", "active_customer_count", "total_ttm_revenue"])

_dt(conc_cust, "evaluation_month")
_num(conc_cust, ["ttm_revenue"])



# ── Metric helpers ───────────────────────────────────────────────────

BIZ_COLORS = {
    "SaaS Platform": CHART_COLORS[0],
    "SaaS Relay":    CHART_COLORS[1],
    "Support Fees":  CHART_COLORS[2],
    "Solutions":     CHART_COLORS[3],
}


def _delta_str(cur, prev, fmt="pct", invert=False):
    if prev == 0:
        return "", None
    pct = (cur - prev) / abs(prev) * 100
    up = pct >= 0
    good = (not up) if invert else up
    arrow = "+" if up else ""
    color = PALETTE["green"] if good else PALETTE["red"]
    if fmt == "pct":
        return f"{arrow}{pct:.1f}% MoM", color
    return f"{arrow}${cur - prev:,.0f} MoM", color


# Reporting cutoff: end of February 2026
CUTOFF = "2026-02-28"

if not decomp.empty:
    decomp = decomp[decomp["report_month"] <= CUTOFF]
    month_biz_count = decomp.groupby("report_month")["business_line"].nunique()
    real_months = month_biz_count[month_biz_count >= 2].index
    decomp = decomp[decomp["report_month"].isin(real_months)]

if not volume.empty:
    volume = volume[volume["report_month"] <= CUTOFF]

if not retention.empty:
    retention = retention[retention["evaluation_month"] <= CUTOFF]



# ══════════════════════════════════════════════════════════════════════
# SECTION 1 — Revenue
# ══════════════════════════════════════════════════════════════════════

st.html(section_label("Revenue"))

# ── Metric cards ─────────────────────────────────────────────────────
if not decomp.empty:
    latest_month = decomp["report_month"].max()
    prev_month = latest_month - pd.DateOffset(months=1)
    cur = decomp[decomp["report_month"] == latest_month]
    prev = decomp[decomp["report_month"] == prev_month]

    cur_gross = cur["gross_revenue"].sum()
    prev_gross = prev["gross_revenue"].sum()
    cur_net = cur["net_revenue"].sum()
    prev_net = prev["net_revenue"].sum()
    cur_new = int(cur["new_customers"].sum())

    d_gross, c_gross = _delta_str(cur_gross, prev_gross)
    d_net, c_net = _delta_str(cur_net, prev_net)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True):
            st.html(metric_card("Gross Revenue", f"${cur_gross:,.0f}", d_gross, c_gross))
    with m2:
        with st.container(border=True):
            st.html(metric_card("Net Revenue", f"${cur_net:,.0f}", d_net, c_net))
    with m3:
        with st.container(border=True):
            exp = cur["expansion_dollars"].sum()
            con = cur["contraction_dollars"].sum()
            net_exp = exp + con
            label = f"+${net_exp:,.0f}" if net_exp >= 0 else f"-${abs(net_exp):,.0f}"
            color = PALETTE["green"] if net_exp >= 0 else PALETTE["red"]
            st.html(metric_card("Net Expansion", label,
                                f"${exp:,.0f} exp / ${abs(con):,.0f} con", color))
    with m4:
        with st.container(border=True):
            st.html(metric_card("New Customers", str(cur_new),
                                f"{latest_month.strftime('%B %Y')}"))

    # ── Revenue trend (stacked area by business line) ────────────────
    c1, c2 = st.columns([3, 2])

    with c1:
        with st.container(border=True):
            st.html(card_header("Gross Revenue", "2025 — present, by business line",
                                source="notion_sync.revenue_decomposition"))
            # Monthly totals for chart (2025+) and YoY comparison
            all_monthly = (decomp.groupby(["report_month", "business_line"])["gross_revenue"]
                           .sum().reset_index().sort_values("report_month"))
            monthly = all_monthly[all_monthly["report_month"] >= "2025-01-01"]

            # Compute YoY % for each month (total gross vs same month prior year)
            month_totals = (decomp.groupby("report_month")["gross_revenue"]
                            .sum().reset_index())
            month_totals["prior_year_month"] = (
                month_totals["report_month"] - pd.DateOffset(years=1))
            prior_lookup = dict(zip(month_totals["report_month"],
                                    month_totals["gross_revenue"]))
            yoy_annotations = {}
            for _, row in month_totals.iterrows():
                m = row["report_month"]
                if m < pd.Timestamp("2025-01-01"):
                    continue
                prior = prior_lookup.get(row["prior_year_month"], 0)
                if prior > 0:
                    pct = (row["gross_revenue"] - prior) / prior * 100
                    yoy_annotations[m] = (pct, row["gross_revenue"])

            fig = go.Figure()
            for biz in ["SaaS Platform", "SaaS Relay", "Support Fees", "Solutions"]:
                d = monthly[monthly["business_line"] == biz]
                if d.empty:
                    continue
                fig.add_trace(go.Bar(
                    x=d["report_month"], y=d["gross_revenue"],
                    name=biz,
                    marker=dict(color=BIZ_COLORS.get(biz, CHART_COLORS[0]),
                                cornerradius=2),
                    hovertemplate="%{x|%b %Y}<br>" + biz + ": <b>$%{y:,.0f}</b><extra></extra>",
                ))

            # Add YoY annotations above each bar
            for m, (pct, total) in yoy_annotations.items():
                sign = "+" if pct >= 0 else ""
                color = PALETTE["green"] if pct >= 0 else PALETTE["red"]
                fig.add_annotation(
                    x=m, y=total,
                    text=f"<b>{sign}{pct:.0f}%</b>",
                    showarrow=False, yshift=12,
                    font=dict(size=10, color=color),
                )

            fig.update_layout(**chart_layout(
                height=340,
                barmode="stack",
                showlegend=True,
                legend=dict(orientation="h", y=-0.12, x=0,
                            font=dict(size=11, color=PALETTE["secondary"])),
                xaxis=dict(gridcolor="rgba(0,0,0,0)"),
                yaxis=dict(gridcolor=PALETTE["grid"], tickprefix="$", tickformat=","),
            ))
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})

    with c2:
        with st.container(border=True):
            st.html(card_header("Business Mix", "% of gross revenue",
                                source="notion_sync.revenue_decomposition"))
            # Monthly share % by business line (2025+)
            mix = (decomp[decomp["report_month"] >= "2025-01-01"]
                   .groupby(["report_month", "business_line"])["gross_revenue"]
                   .sum().reset_index())
            mix_totals = mix.groupby("report_month")["gross_revenue"].transform("sum")
            mix["share_pct"] = (mix["gross_revenue"] / mix_totals * 100).round(1)

            fig = go.Figure()
            for biz in ["SaaS Platform", "SaaS Relay", "Support Fees", "Solutions"]:
                d = mix[mix["business_line"] == biz].sort_values("report_month")
                if d.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=d["report_month"], y=d["share_pct"],
                    name=biz, stackgroup="one",
                    line=dict(width=0.5, color=BIZ_COLORS.get(biz, CHART_COLORS[0])),
                    hovertemplate="%{x|%b %Y}<br>" + biz + ": <b>%{y:.1f}%</b><extra></extra>",
                ))
            fig.update_layout(**chart_layout(
                height=340,
                showlegend=True,
                legend=dict(orientation="h", y=-0.12, x=0,
                            font=dict(size=11, color=PALETTE["secondary"])),
                xaxis=dict(gridcolor="rgba(0,0,0,0)"),
                yaxis=dict(gridcolor=PALETTE["grid"], range=[0, 100],
                           ticksuffix="%"),
            ))
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})

    # ── Net expansion waterfall ──────────────────────────────────────
    # ── NRR / GRR + TTM Movement ──────────────────────────────────────
    if not retention.empty:
        # Compute NRR & GRR per month from retention summary
        existing_cats = ["expansion", "contraction", "flat", "churned"]
        ret_existing = retention[retention["retention_category"].isin(existing_cats)]
        ret_monthly = (ret_existing.groupby("evaluation_month")
                       .agg(ttm_cur=("ttm_current", "sum"),
                            ttm_prior=("ttm_prior", "sum"))
                       .reset_index().sort_values("evaluation_month"))
        ret_monthly["nrr"] = (ret_monthly["ttm_cur"] / ret_monthly["ttm_prior"] * 100).round(1)

        # GRR = (prior - contraction_loss - churn_loss) / prior
        loss_cats = ["contraction", "churned"]
        ret_loss = (retention[retention["retention_category"].isin(loss_cats)]
                    .groupby("evaluation_month")["ttm_delta"].sum().reset_index())
        ret_loss.columns = ["evaluation_month", "loss_delta"]
        ret_monthly = ret_monthly.merge(ret_loss, on="evaluation_month", how="left")
        ret_monthly["loss_delta"] = ret_monthly["loss_delta"].fillna(0)
        ret_monthly["grr"] = ((ret_monthly["ttm_prior"] + ret_monthly["loss_delta"])
                              / ret_monthly["ttm_prior"] * 100).round(1)

        # Filter to 2025+
        ret_monthly = ret_monthly[ret_monthly["evaluation_month"] >= "2025-01-01"]

        # NRR/GRR metric cards
        latest_ret = ret_monthly.iloc[-1] if len(ret_monthly) > 0 else None
        prev_ret = ret_monthly.iloc[-2] if len(ret_monthly) > 1 else None

        if latest_ret is not None:
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    nrr = latest_ret["nrr"]
                    nrr_color = PALETTE["green"] if nrr >= 100 else PALETTE["red"]
                    sub = ""
                    if prev_ret is not None:
                        d = nrr - prev_ret["nrr"]
                        sub = f"{'+' if d >= 0 else ''}{d:.1f}pp MoM"
                    st.html(metric_card("Net Revenue Retention", f"{nrr:.1f}%", sub, nrr_color))
            with c2:
                with st.container(border=True):
                    grr = latest_ret["grr"]
                    grr_color = PALETTE["green"] if grr >= 90 else PALETTE["amber"] if grr >= 80 else PALETTE["red"]
                    sub = ""
                    if prev_ret is not None:
                        d = grr - prev_ret["grr"]
                        sub = f"{'+' if d >= 0 else ''}{d:.1f}pp MoM"
                    st.html(metric_card("Gross Revenue Retention", f"{grr:.1f}%", sub, grr_color))

        # NRR/GRR trend + TTM movement stacked bar
        c1, c2 = st.columns([3, 2])

        with c1:
            with st.container(border=True):
                st.html(card_header("NRR & GRR Trend", "trailing 12-month, existing customers",
                                    source="notion_sync.revenue_retention_summary"))
                fig = go.Figure()
                # 100% reference line
                fig.add_hline(y=100, line_dash="dot", line_color=PALETTE["secondary"],
                              line_width=1, opacity=0.5)
                fig.add_trace(go.Scatter(
                    x=ret_monthly["evaluation_month"], y=ret_monthly["nrr"],
                    name="NRR", mode="lines",
                    line=dict(color=CHART_COLORS[0], width=2.5, shape="spline"),
                    hovertemplate="%{x|%b %Y}<br>NRR: <b>%{y:.1f}%</b><extra></extra>",
                ))
                fig.add_trace(go.Scatter(
                    x=ret_monthly["evaluation_month"], y=ret_monthly["grr"],
                    name="GRR", mode="lines",
                    line=dict(color=PALETTE["amber"], width=2.5, shape="spline"),
                    hovertemplate="%{x|%b %Y}<br>GRR: <b>%{y:.1f}%</b><extra></extra>",
                ))
                fig.update_layout(**chart_layout(
                    height=300,
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.15, x=0,
                                font=dict(size=11, color=PALETTE["secondary"])),
                    xaxis=dict(gridcolor="rgba(0,0,0,0)"),
                    yaxis=dict(gridcolor=PALETTE["grid"], ticksuffix="%"),
                ))
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False})

        with c2:
            with st.container(border=True):
                st.html(card_header("TTM Movement", "by retention category",
                                    source="notion_sync.revenue_retention_summary"))
                # Pivot retention categories into columns for stacked bar
                move = (retention[retention["evaluation_month"] >= "2025-01-01"]
                        .groupby(["evaluation_month", "retention_category"])["ttm_delta"]
                        .sum().reset_index().sort_values("evaluation_month"))

                cat_colors = {
                    "expansion": PALETTE["green"],
                    "new": CHART_COLORS[0],
                    "reactivation": CHART_COLORS[1],
                    "flat": PALETTE["secondary"],
                    "contraction": PALETTE["amber"],
                    "churned": PALETTE["red"],
                }
                fig = go.Figure()
                for cat in ["expansion", "new", "reactivation", "contraction", "churned"]:
                    d = move[move["retention_category"] == cat]
                    if d.empty:
                        continue
                    fig.add_trace(go.Bar(
                        x=d["evaluation_month"], y=d["ttm_delta"],
                        name=cat.title(), marker=dict(color=cat_colors.get(cat, CHART_COLORS[0]),
                                                      cornerradius=3),
                        hovertemplate="%{x|%b %Y}<br>" + cat.title() + ": <b>$%{y:,.0f}</b><extra></extra>",
                    ))
                fig.update_layout(**chart_layout(
                    height=300,
                    barmode="relative",
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.15, x=0,
                                font=dict(size=11, color=PALETTE["secondary"])),
                    xaxis=dict(gridcolor="rgba(0,0,0,0)"),
                    yaxis=dict(gridcolor=PALETTE["grid"], tickprefix="$", tickformat=","),
                ))
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════
# SECTION 2 — Volume & Unit Economics
# ══════════════════════════════════════════════════════════════════════

st.html(section_label("Volume & Unit Economics"))

if not unit_econ.empty:
    # Latest month unit economics by business line
    ue_latest_month = unit_econ["report_month"].max()
    ue_latest = unit_econ[unit_econ["report_month"] == ue_latest_month]
    ue_prev_month = ue_latest_month - pd.DateOffset(months=1)
    ue_prev = unit_econ[unit_econ["report_month"] == ue_prev_month]

    plat = ue_latest[ue_latest["business_line"] == "SaaS Platform"]
    relay = ue_latest[ue_latest["business_line"] == "SaaS Relay"]
    plat_prev = ue_prev[ue_prev["business_line"] == "SaaS Platform"]
    relay_prev = ue_prev[ue_prev["business_line"] == "SaaS Relay"]

    total_vol = ue_latest["volume"].sum()
    prev_total_vol = ue_prev["volume"].sum()
    plat_vol = int(plat["volume"].sum()) if not plat.empty else 0
    relay_vol = int(relay["volume"].sum()) if not relay.empty else 0
    plat_fee = plat["processing_per_scan"].iloc[0] if not plat.empty else 0
    relay_fee = relay["processing_per_scan"].iloc[0] if not relay.empty else 0
    plat_fee_prev = plat_prev["processing_per_scan"].iloc[0] if not plat_prev.empty else 0
    relay_fee_prev = relay_prev["processing_per_scan"].iloc[0] if not relay_prev.empty else 0

    v_delta, v_color = _delta_str(total_vol, prev_total_vol)
    pf_delta, pf_color = _delta_str(plat_fee, plat_fee_prev)
    rf_delta, rf_color = _delta_str(relay_fee, relay_fee_prev)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True):
            st.html(metric_card("Total Volume", f"{int(total_vol):,}",
                                v_delta, v_color))
    with m2:
        with st.container(border=True):
            st.html(metric_card("Platform Fee/Scan", f"${plat_fee:.2f}",
                                pf_delta, pf_color))
    with m3:
        with st.container(border=True):
            st.html(metric_card("Relay Fee/Scan", f"${relay_fee:.2f}",
                                rf_delta, rf_color))
    with m4:
        with st.container(border=True):
            ratio = relay_vol / plat_vol if plat_vol > 0 else 0
            st.html(metric_card("Relay : Platform", f"{ratio:.1f}x",
                                f"{relay_vol:,} vs {plat_vol:,} scans"))

    # ── Weekly volume pulse + fee decomposition ─────────────────────
    c1, c2 = st.columns([3, 2])

    with c1:
        with st.container(border=True):
            st.html(card_header("Weekly Volume Pulse", "contract vs relay",
                                source="notion_sync.volume_weekly"))
            if not vol_weekly.empty:
                wk = (vol_weekly.groupby(["period_start", "business_line"])["volume"]
                      .sum().reset_index().sort_values("period_start"))

                fig = go.Figure()
                # Relay as light filled area (background)
                relay_wk = wk[wk["business_line"] == "SaaS Relay"]
                if not relay_wk.empty:
                    fig.add_trace(go.Bar(
                        x=relay_wk["period_start"], y=relay_wk["volume"],
                        name="Relay", marker=dict(color="rgba(43,123,233,0.15)",
                                                  cornerradius=2),
                        hovertemplate="%{x|%b %d}<br>Relay: <b>%{y:,.0f}</b><extra></extra>",
                        yaxis="y2",
                    ))
                # Platform as solid bars (foreground)
                plat_wk = wk[wk["business_line"] == "SaaS Platform"]
                if not plat_wk.empty:
                    fig.add_trace(go.Bar(
                        x=plat_wk["period_start"], y=plat_wk["volume"],
                        name="Platform", marker=dict(color=CHART_COLORS[0],
                                                     cornerradius=2),
                        hovertemplate="%{x|%b %d}<br>Platform: <b>%{y:,.0f}</b><extra></extra>",
                    ))

                fig.update_layout(**chart_layout(
                    height=340,
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.12, x=0,
                                font=dict(size=11, color=PALETTE["secondary"])),
                    barmode="overlay",
                    xaxis=dict(gridcolor="rgba(0,0,0,0)",
                               rangebreaks=[dict(bounds=["sat", "mon"])]),
                    yaxis=dict(gridcolor=PALETTE["grid"], tickformat=",",
                               title=dict(text="Platform", font=dict(size=10, color=PALETTE["secondary"]))),
                    yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                tickformat=",",
                                title=dict(text="Relay", font=dict(size=10, color=PALETTE["secondary"]))),
                ))
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False})

    with c2:
        with st.container(border=True):
            st.html(card_header("Revenue per Scan", "fee decomposition, Platform",
                                source="notion_sync.unit_economics_monthly"))
            # Stacked area: processing + gov + sam per scan over time (Platform only)
            plat_ue = (unit_econ[(unit_econ["business_line"] == "SaaS Platform") &
                                (unit_econ["report_month"] >= "2025-01-01")]
                       .sort_values("report_month"))
            if not plat_ue.empty:
                fig = go.Figure()
                for col, label, color in [
                    ("processing_per_scan", "Processing", CHART_COLORS[0]),
                    ("gov_per_scan", "Gov Fee", CHART_COLORS[2]),
                    ("sam_per_scan", "SAM Fee", CHART_COLORS[1]),
                ]:
                    vals = plat_ue[col].fillna(0)
                    fig.add_trace(go.Scatter(
                        x=plat_ue["report_month"], y=vals,
                        name=label, stackgroup="one",
                        line=dict(width=0.5, color=color),
                        hovertemplate="%{x|%b %Y}<br>" + label + ": <b>$%{y:.2f}</b><extra></extra>",
                    ))
                fig.update_layout(**chart_layout(
                    height=340,
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.12, x=0,
                                font=dict(size=11, color=PALETTE["secondary"])),
                    xaxis=dict(gridcolor="rgba(0,0,0,0)"),
                    yaxis=dict(gridcolor=PALETTE["grid"], tickprefix="$"),
                ))
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False})

    # ── Fee trend: Platform vs Relay ────────────────────────────────
    with st.container(border=True):
        st.html(card_header("Processing Fee Trend", "platform vs relay, per scan",
                            source="notion_sync.unit_economics_monthly"))
        fee_trend = (unit_econ[unit_econ["report_month"] >= "2025-01-01"]
                     .sort_values("report_month"))
        fig = go.Figure()
        for biz, color in [("SaaS Platform", CHART_COLORS[0]), ("SaaS Relay", CHART_COLORS[1])]:
            d = fee_trend[fee_trend["business_line"] == biz]
            if d.empty:
                continue
            fig.add_trace(go.Scatter(
                x=d["report_month"], y=d["processing_per_scan"],
                name=biz, mode="lines+markers",
                line=dict(color=color, width=2.5, shape="spline"),
                marker=dict(size=5),
                hovertemplate="%{x|%b %Y}<br>" + biz + ": <b>$%{y:.2f}</b>/scan<extra></extra>",
            ))
        fig.update_layout(**chart_layout(
            height=260,
            showlegend=True,
            legend=dict(orientation="h", y=-0.18, x=0,
                        font=dict(size=11, color=PALETTE["secondary"])),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"),
            yaxis=dict(gridcolor=PALETTE["grid"], tickprefix="$"),
        ))
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════
# SECTION 4 — Customer Concentration
# ══════════════════════════════════════════════════════════════════════

st.html(section_label("Customer Concentration"))

BUCKET_COLORS = {
    "SaaS":            CHART_COLORS[0],
    "Partner":         CHART_COLORS[1],
    "Law Enforcement": CHART_COLORS[2],
    "Service Center":  CHART_COLORS[3],
}

if not conc_cust.empty:
    # Aggregate by client — customers span multiple business lines
    latest_eval = conc_cust["evaluation_month"].max()
    cust_latest = conc_cust[conc_cust["evaluation_month"] == latest_eval]
    top_cust = (cust_latest.groupby(["client_id", "customer_name"])
                .agg(ttm=("ttm_revenue", "sum"),
                     bucket=("accounting_bucket", "first"),
                     lines=("business_line", lambda x: ", ".join(sorted(x.unique()))))
                .reset_index().sort_values("ttm", ascending=False))
    total_ttm = top_cust["ttm"].sum()
    top_cust["share_pct"] = (top_cust["ttm"] / total_ttm * 100).round(2)
    top_cust["cumulative_pct"] = top_cust["share_pct"].cumsum().round(1)

    # ── Metric cards ────────────────────────────────────────────────
    top1 = top_cust.iloc[0]
    top3_share = top_cust.head(3)["share_pct"].sum()
    top5_share = top_cust.head(5)["share_pct"].sum()
    top10_share = top_cust.head(10)["share_pct"].sum()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True):
            st.html(metric_card("#1 Customer", top1["customer_name"],
                                f"{top1['share_pct']:.1f}% · ${top1['ttm']:,.0f} TTM",
                                PALETTE["amber"]))
    with m2:
        with st.container(border=True):
            st.html(metric_card("Top-3 Share", f"{top3_share:.1f}%",
                                f"${top_cust.head(3)['ttm'].sum():,.0f} TTM"))
    with m3:
        with st.container(border=True):
            st.html(metric_card("Top-5 Share", f"{top5_share:.1f}%",
                                f"${top_cust.head(5)['ttm'].sum():,.0f} TTM"))
    with m4:
        with st.container(border=True):
            st.html(metric_card("Top-10 Share", f"{top10_share:.1f}%",
                                f"{len(top_cust):,} active customers"))

    # ── Top 10 customers + concentration trend ──────────────────────
    c1, c2 = st.columns([3, 2])

    with c1:
        with st.container(border=True):
            st.html(card_header("Top 10 Customers", "trailing 12-month revenue",
                                source="notion_sync.customer_concentration_top"))
            top10 = top_cust.head(10).sort_values("ttm")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=top10["customer_name"], x=top10["ttm"],
                orientation="h",
                marker=dict(
                    color=[BUCKET_COLORS.get(b, CHART_COLORS[0]) for b in top10["bucket"]],
                    cornerradius=4,
                ),
                text=[f"{s:.1f}%" for s in top10["share_pct"]],
                textposition="outside", textfont=dict(size=10, color=PALETTE["secondary"]),
                hovertemplate="%{y}<br><b>$%{x:,.0f}</b> TTM<extra></extra>",
            ))
            fig.update_layout(**chart_layout(
                height=380,
                margin=dict(l=0, r=50, t=8, b=0),
                xaxis=dict(gridcolor=PALETTE["grid"], tickprefix="$", tickformat=","),
                yaxis=dict(gridcolor="rgba(0,0,0,0)", automargin=True),
            ))
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})

    with c2:
        with st.container(border=True):
            st.html(card_header("Concentration Trend", "top-N share of TTM revenue",
                                source="notion_sync.customer_concentration_trend"))
            # Filter to Overall / All Revenue, 2025+
            trend = conc_trend[
                (conc_trend["cut_dimension"] == "Overall") &
                (conc_trend["cut_value"] == "All Revenue") &
                (conc_trend["evaluation_month"] >= "2025-01-01")
            ].sort_values("evaluation_month")

            if not trend.empty:
                fig = go.Figure()
                for col, label, color in [
                    ("top1_share_pct",  "Top-1",  PALETTE["red"]),
                    ("top5_share_pct",  "Top-5",  PALETTE["amber"]),
                    ("top10_share_pct", "Top-10", CHART_COLORS[0]),
                    ("top20_share_pct", "Top-20", PALETTE["secondary"]),
                ]:
                    fig.add_trace(go.Scatter(
                        x=trend["evaluation_month"], y=trend[col],
                        name=label, mode="lines",
                        line=dict(color=color, width=2.5, shape="spline"),
                        hovertemplate="%{x|%b %Y}<br>" + label + ": <b>%{y:.1f}%</b><extra></extra>",
                    ))
                fig.update_layout(**chart_layout(
                    height=380,
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.15, x=0,
                                font=dict(size=11, color=PALETTE["secondary"])),
                    xaxis=dict(gridcolor="rgba(0,0,0,0)"),
                    yaxis=dict(gridcolor=PALETTE["grid"], ticksuffix="%",
                               range=[0, 75]),
                ))
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False})

    # ── Revenue treemap — top 20 customers ──────────────────────────
    with st.container(border=True):
        st.html(card_header("Revenue Landscape", "top 20 customers by TTM revenue, grouped by segment",
                            source="notion_sync.customer_concentration_top"))
        top20 = top_cust.head(20).copy()
        top20["label"] = (top20["customer_name"] + "<br>"
                          + top20["share_pct"].apply(lambda x: f"{x:.1f}%")
                          + " · $" + top20["ttm"].apply(lambda x: f"{x:,.0f}"))

        fig = go.Figure(go.Treemap(
            labels=top20["label"],
            parents=top20["bucket"],
            values=top20["ttm"],
            textinfo="label",
            textfont=dict(size=11),
            marker=dict(
                colors=[BUCKET_COLORS.get(b, CHART_COLORS[0]) for b in top20["bucket"]],
                line=dict(width=2, color="white"),
            ),
            hovertemplate="<b>%{label}</b><extra></extra>",
        ))
        fig.update_layout(**chart_layout(
            height=400,
            margin=dict(l=0, r=0, t=28, b=0),
        ))
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})
