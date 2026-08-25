"""
AUTHOR: Arthur Briens
DATE: 17/08/2026

                            __
     ,                    ," e`--o
    ((                   (  | __,'
     \\~----------------' \_;/
     (                      /
     /) ._______________.  )
    (( (               (( (
     ``-'               ``-'
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import theme as T  # noqa: E402

st.set_page_config(page_title="Circularity dashboard - Brazil and France", layout="wide")
T.register_templates()

dark = st.sidebar.toggle("Dark mode", value=False, key="home_dark")
P = T.palette(dark)
st.markdown(T.page_css(dark), unsafe_allow_html=True)

# --------------------------------------------------------------------------
# hero
# --------------------------------------------------------------------------

st.title("USP–PSL Circular Economy Institute")
st.markdown(
    "Comparative research on EPR systems, circularity targets, and waste "
    "management practices in **France** and **Brazil**."
)

st.divider()

# --------------------------------------------------------------------------
# about
# --------------------------------------------------------------------------

col_about, col_flag = st.columns([3, 1])

with col_about:
    st.subheader("About the project")
    st.markdown(
        "The [USP–PSL Institute for Circular Economy]"
        "(https://psl.eu/actualites/luniversite-psl-setablit-au-bresil-inauguration-du-nouvel-institut-universitaire-psl-usp) "
        "is a joint initiative between Brazil and France. "
        "It combines expertise in economics, chemistry, and physics to produce "
        "research and insights for academics, policy-makers, and businesses."
    )

with col_flag:
    st.markdown(
        "<div style='font-size:64px; text-align:center; padding-top:8px'>🇧🇷 🇫🇷</div>",
        unsafe_allow_html=True,
    )

st.divider()

# --------------------------------------------------------------------------
# page navigation
# --------------------------------------------------------------------------

st.subheader("Explore the dashboard")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("##### Circularity Targets")
    st.caption(
        "Government and sector-specific recycling targets set by France and Brazil — "
        "EU directives, PNRS / Planares, and reverse-logistics agreements."
    )
    st.page_link("pages/2_targets.py", label="Open Targets page", icon="🎯")

with c2:
    st.markdown("##### EPR Eco-organisations")
    st.caption(
        "Overview of French EPR eco-organisations (*éco-organismes*) by filière: "
        "tonnage collected, quantities managed, and market structure."
    )
    st.page_link("pages/3_EPR.py", label="Open EPR overview", icon="♻️")

with c3:
    st.markdown("##### France — EPR Filieres detail")
    st.caption(
        "Filière-level performance against REP collection and recycling targets, "
        "with regional breakdowns and treatment-location analysis."
    )
    st.page_link("pages/4_France_EPR.py", label="Open France EPR detail", icon="🔍")