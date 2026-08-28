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

import streamlit as st

pg = st.navigation([
    st.Page("pages/home.py", title="Home"),
    st.Page("pages/2_targets.py", title="Environmental targets - Brazil and France"),
    st.Page("pages/3_EPR.py", title="Market structures of EPRs - France"),
    st.Page("pages/4_France_EPR.py", title="Evolution of targets for EPRs"),
])
pg.run()