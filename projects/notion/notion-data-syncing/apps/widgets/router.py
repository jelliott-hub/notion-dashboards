"""Widget router — single Streamlit entrypoint for all embeddable widgets.

Deploy once on Streamlit Cloud. Access widgets via query param:
    ?widget=support_call_volume
    ?widget=support_call_mix&height=400

Run locally:
    streamlit run apps/widgets/router.py
"""

import sys
import os
import importlib

# Ensure project root is on sys.path so core.* imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st

from apps.widgets._registry import WIDGETS

_WIDGET_IDS = {w["id"] for w in WIDGETS}

widget_id = st.query_params.get("widget", "catalog")

if widget_id == "catalog":
    mod = importlib.import_module("apps.widgets.catalog")
    mod.render()
elif widget_id in _WIDGET_IDS:
    mod = importlib.import_module(f"apps.widgets.{widget_id}")
    mod.render()
else:
    st.set_page_config(page_title="Unknown Widget", page_icon="◆", layout="wide")
    st.error(f"Unknown widget: `{widget_id}`")
    st.info("Use `?widget=catalog` to see all available widgets.")
