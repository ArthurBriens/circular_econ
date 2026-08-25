"""
AUTHOR: Arthur Briens
DATE: 19/08/2026

France -- EPR (REP) filieres. Collection, treatment and eco-organism structure.

Reading order: status -> trajectory -> mechanism -> territory. Charts marked
PLACEHOLDER are shape-only: the underlying figures are not in data/raw yet.

                            __
     ,                    ," e`--o
    ((                   (  | __,'
     \\~----------------' \_;/
     (                      /
     /) ._______________.  )
    (( (               (( (
     ``-'               ``-'
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import data as D          # noqa: E402
from lib import theme as T         # noqa: E402

st.set_page_config(page_title="France - EPR filieres", layout="wide")
T.register_templates()

# --------------------------------------------------------------------------
# controls -- one filter set for the whole page
# --------------------------------------------------------------------------

with st.sidebar:
    st.header("Filters")
    dark = st.toggle("Dark mode", value=False)
    codes = st.multiselect(
        "Filiere",
        options=list(D.FILIERE_EN),
        default=D.FLAGSHIP,
        format_func=lambda c: f"{c} - {D.FILIERE_EN.get(c, c)}",
    )
    year = st.select_slider("Year", options=list(range(2017, 2025)), value=2024)

P = T.palette(dark)
TPL = T.template_name(dark)
NEUTRAL = "#c3c2b7" if not dark else "#52514e"
st.markdown(T.page_css(dark), unsafe_allow_html=True)

if not codes:
    st.info("Select at least one filiere in the sidebar.")
    st.stop()

msm = D.load_msm()
trt = D.load_treatment()
actors = D.load_actors()


# theme=None is REQUIRED: st.plotly_chart defaults to theme="streamlit",
# which overrides the registered template's surface and font colours --
# in dark mode that left every plot area white under a dark page.
def chart(fig: go.Figure, height: int = 320) -> go.Figure:
    fig.update_layout(
        template=TPL, height=height, margin=dict(l=8, r=8, t=28, b=8),
        # set EXPLICITLY, not just via the template: Streamlit merges its own
        # config.toml colours over a figure's template defaults, so the template's
        # paper/plot colour loses and the plot area stayed light in dark mode.
        # An explicit layout value on the figure itself wins that merge.
        paper_bgcolor=P["surface"], plot_bgcolor=P["surface"],
    )
    return fig


st.title("France - EPR filieres")
st.caption(
    "Extended Producer Responsibility. Source: ADEME / SYDEREP extracts in "
    "data/raw. Declarations are national by eco-organism; the treatment file "
    "is resolved to the TREATMENT SITE, not the point of collection."
)

# ==========================================================================
# A. headline figures
# ==========================================================================

st.markdown('<div class="sect">A - Where France stands</div>', unsafe_allow_html=True)

msm_y = msm[(msm.filiere.isin(codes)) & (msm.annee == year)]
msm_prev = msm[(msm.filiere.isin(codes)) & (msm.annee == year - 1)]
trt_y = trt[(trt.filiere.isin(codes)) & (trt.annee == year)]

put_on_market = msm_y.tonnage.sum()
prev_pom = msm_prev.tonnage.sum()
treated = trt_y.masse.sum()
reuse = trt_y.loc[trt_y.bucket == "Reuse", "masse"].sum()
ratio = treated / put_on_market * 100 if put_on_market else 0

k1, k2, k3, k4 = st.columns([1.35, 1, 1, 1])
with k1:
    # the hero figure -- enlarged via the first-column rule in theme.page_css
    st.metric("Treated tonnage as a share of tonnage put on market",
              f"{ratio:,.1f} %",
              help="Computed proxy, not the published collection rate. "
                   "The separate collection dataset is not in data/raw yet.")
with k2:
    delta = (put_on_market / prev_pom - 1) * 100 if prev_pom else None
    st.metric("Put on market", f"{put_on_market/1e6:,.2f} Mt",
              delta=f"{delta:,.1f} % vs {year-1}" if delta is not None else None)
with k3:
    st.metric("Treated tonnage", f"{treated/1e3:,.0f} kt")
with k4:
    st.metric("Of which reuse", f"{reuse/1e3:,.1f} kt")

# ==========================================================================
# B. gap to target -- anchor chart
# ==========================================================================

st.markdown('<div class="sect">B - Gap to regulatory target</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="caveat"><b>PLACEHOLDER targets.</b> The regulatory collection '
    'targets are not in the downloaded extracts. The bars are computed from real '
    'data (treated / put on market); the target ticks are stand-in values from '
    '<code>lib/data.PLACEHOLDER_TARGETS</code>. Replace them with the published '
    'figures from the ADEME filiere fact sheets before drawing any conclusion.</div>',
    unsafe_allow_html=True,
)

rows = []
for c in codes:
    pom = msm_y.loc[msm_y.filiere == c, "tonnage"].sum()
    tre = trt_y.loc[trt_y.filiere == c, "masse"].sum()
    if pom > 0 and tre > 0:
        rows.append({
            "filiere": c,
            "label": f"{c} - {D.FILIERE_EN.get(c, c)}",
            "rate": min(tre / pom * 100, 100),
            "target": D.PLACEHOLDER_TARGETS.get(c),
        })

if rows:
    b = pd.DataFrame(rows).sort_values("rate")
    fig = go.Figure()
    fig.add_bar(y=b.label, x=[100] * len(b), orientation="h",
                marker_color=P["track"], hoverinfo="skip", showlegend=False,
                width=0.42)
    fig.add_bar(y=b.label, x=b.rate, orientation="h",
                marker_color=P["series"][0], width=0.42, showlegend=False,
                text=[f"{v:,.1f} %" for v in b.rate], textposition="outside",
                textfont=dict(color=P["text_primary"], size=12),
                hovertemplate="%{y}<br>Treated / put on market: %{x:,.1f} %<extra></extra>")
    tg = b.dropna(subset=["target"])
    if not tg.empty:
        # colour set explicitly: left to the colorway this picks up series slot 3
        # (green), which reads as a status cue it is not
        fig.add_scatter(y=tg.label, x=tg.target, mode="markers",
                        marker=dict(symbol="line-ns-open", size=26,
                                    color=P["text_primary"],
                                    line=dict(color=P["text_primary"], width=2)),
                        name="Target (placeholder)",
                        hovertemplate="%{y}<br>Target: %{x:,.1f} %<extra></extra>")
    fig.update_layout(barmode="overlay", xaxis=dict(range=[0, 105], ticksuffix=" %"),
                      yaxis=dict(showgrid=False))
    st.plotly_chart(chart(fig, 90 + 52 * len(b)), use_container_width=True, theme=None)

    dropped = [c for c in codes if c not in set(b.filiere)]
    if dropped:
        # say so rather than letting rows vanish -- a filiere silently missing
        # from a ranking reads as "not applicable" instead of "no data"
        st.caption(
            "Not shown for lack of put-on-market or treatment data in "
            f"{year}: {', '.join(dropped)}."
        )

    with st.expander("Table view"):
        st.dataframe(
            b.rename(columns={"label": "Filiere", "rate": "Treated / put on market (%)",
                              "target": "Target (placeholder, %)"})
             .drop(columns="filiere").set_index("Filiere").round(1),
            use_container_width=True,
        )
else:
    st.info("No filiere in the current selection has both put-on-market and "
            f"treatment data for {year}.")

# ==========================================================================
# C + D. trajectories and treatment mix
# ==========================================================================

st.markdown('<div class="sect">C - Trajectories &nbsp;.&nbsp; D - Treatment mix</div>',
            unsafe_allow_html=True)
c_left, c_right = st.columns([7, 5])

with c_left:
    st.subheader("Tonnage put on market, indexed to first year = 100")
    st.caption("Indexed so filieres three orders of magnitude apart share one "
               "axis. Absolute tonnages are in the table below.")
    series = D.msm_by_year(msm, codes)
    panels = codes[:6]
    ncol = 2
    nrow = -(-len(panels) // ncol)
    fig = make_subplots(rows=nrow, cols=ncol, shared_yaxes=True,
                        subplot_titles=[f"{c} - {D.FILIERE_EN.get(c, c)}" for c in panels],
                        vertical_spacing=0.18, horizontal_spacing=0.08)
    for i, c in enumerate(panels):
        s = series[series.filiere == c].sort_values("annee")
        if s.empty or s.tonnage.iloc[0] == 0:
            continue
        idx = s.tonnage / s.tonnage.iloc[0] * 100
        r, col = i // ncol + 1, i % ncol + 1
        fig.add_scatter(x=s.annee, y=idx, mode="lines", row=r, col=col,
                        line=dict(color=P["series"][0], width=2),
                        showlegend=False,
                        hovertemplate=f"{c} %{{x}}<br>Index: %{{y:,.0f}}<extra></extra>")
        fig.add_scatter(x=[s.annee.iloc[-1]], y=[idx.iloc[-1]], mode="markers+text",
                        row=r, col=col, marker=dict(color=P["series"][0], size=8,
                                                    line=dict(color=P["surface"], width=2)),
                        text=[f"{idx.iloc[-1]:,.0f}"], textposition="middle right",
                        textfont=dict(color=P["text_primary"], size=11),
                        showlegend=False, hoverinfo="skip")
        fig.add_hline(y=100, row=r, col=col, line_width=1, line_color=P["axis"])
        # headroom on the right, or the end label is clipped by the panel edge
        span = s.annee.iloc[-1] - s.annee.iloc[0]
        fig.update_xaxes(range=[s.annee.iloc[0] - span * 0.04,
                                s.annee.iloc[-1] + span * 0.30],
                         row=r, col=col)
    for a in fig.layout.annotations:
        a.font.size = 12
        a.font.color = P["text_primary"]
    st.plotly_chart(chart(fig, 160 * nrow + 60), use_container_width=True, theme=None)

with c_right:
    st.subheader(f"Where treated tonnage ends up, {year}")
    st.caption("Ordered by the waste hierarchy, darkest first. Unclassified is "
               "shown, not hidden -- see the code-mapping note at the bottom.")
    mix, skipped = D.treatment_mix(trt, codes, year)
    if skipped:
        st.caption(
            "No treatment code declared in "
            f"{year}, so excluded here: {', '.join(skipped)}. "
            "These filieres report supported tonnage rather than treatment "
            "operations -- an absent breakdown, not a zero."
        )
    if mix.empty:
        st.info(f"No coded treatment declarations for this selection in {year}.")
    else:
        fig = go.Figure()
        ramp = dict(zip(D.HIERARCHY[:4], P["ordinal"]))
        ramp["Unclassified"] = NEUTRAL
        for bucket in D.HIERARCHY:
            part = mix[mix.bucket == bucket]
            if part.empty:
                continue
            fig.add_bar(y=part.filiere, x=part.share, orientation="h", name=bucket,
                        marker=dict(color=ramp[bucket],
                                    line=dict(color=P["surface"], width=2)),
                        hovertemplate="%{y} - " + bucket + ": %{x:,.1f} %<extra></extra>")
        fig.update_layout(barmode="stack",
                          xaxis=dict(ticksuffix=" %", range=[0, 100]),
                          yaxis=dict(showgrid=False))
        st.plotly_chart(chart(fig, 120 + 46 * mix.filiere.nunique()),
                        use_container_width=True, theme=None)

# ==========================================================================
# E. eco-organism structure
# ==========================================================================

st.markdown('<div class="sect">E - By eco-organism</div>', unsafe_allow_html=True)

# declared BEFORE the columns: Streamlit renders in call order, so a control
# created after st.columns() lands underneath the charts it drives
focus = st.selectbox("Filiere in focus", options=codes,
                     format_func=lambda c: f"{c} - {D.FILIERE_EN.get(c, c)}")
by_actor = D.msm_by_actor(msm, actors, focus)

e_left, e_right = st.columns([7, 5])

with e_left:
    st.subheader(f"Tonnage put on market by declaring body - {focus}")
    st.caption("Shows how share moved as filieres opened to competing "
               "eco-organisms. A single-body filiere shows one series: that is "
               "the monopoly case, not missing data.")
    top = (by_actor.groupby("name")["tonnage"].sum()
           .sort_values(ascending=False).head(8).index.tolist())
    fig = go.Figure()
    for i, name in enumerate(top):
        s = by_actor[by_actor.name == name].sort_values("annee")
        fig.add_bar(x=s.annee, y=s.tonnage / 1e3, name=name,
                    marker=dict(color=P["series"][i % 8],
                                line=dict(color=P["surface"], width=2)),
                    hovertemplate=f"{name} %{{x}}<br>%{{y:,.0f}} kt<extra></extra>")
    fig.update_layout(barmode="stack", yaxis_title="kt", xaxis=dict(showgrid=False))
    st.plotly_chart(chart(fig, 340), use_container_width=True, theme=None)

with e_right:
    st.subheader("Share of the filiere, first to last year")
    st.caption("Slope of each body's share. Crossing lines are the story: a "
               "change in who carries the filiere.")
    yrs = sorted(by_actor.annee.unique())
    if len(yrs) >= 2:
        first, last = yrs[0], yrs[-1]
        fig = go.Figure()
        for i, name in enumerate(top):
            s = by_actor[by_actor.name == name]
            a = s.loc[s.annee == first, "share"]
            z = s.loc[s.annee == last, "share"]
            if a.empty or z.empty:
                continue
            fig.add_scatter(x=[first, last], y=[a.iloc[0], z.iloc[0]],
                            mode="lines+markers", name=name,
                            line=dict(color=P["series"][i % 8], width=2),
                            marker=dict(size=8, line=dict(color=P["surface"], width=2)),
                            hovertemplate=f"{name} %{{x}}<br>%{{y:,.1f}} %<extra></extra>")
        fig.update_layout(xaxis=dict(tickvals=[first, last], showgrid=False),
                          yaxis=dict(ticksuffix=" %"))
        st.plotly_chart(chart(fig, 340), use_container_width=True, theme=None)
    else:
        st.info("Only one year of declarations for this filiere.")

# ==========================================================================
# F. treated in France vs abroad
# ==========================================================================

st.markdown('<div class="sect">F - Domestic vs exported treatment</div>',
            unsafe_allow_html=True)
st.caption("Substitutes for the collection-channel chart in the mockup: the "
           "`origine de collecte` field lives in a dataset not yet downloaded. "
           "This uses `pays_site_trt`, which is present.")

dom = D.domestic_split(trt, codes, year)
if dom.empty:
    st.info(f"No treatment declarations for this selection in {year}.")
else:
    fig = go.Figure()
    # "not declared" is an absence, so it wears the neutral, not a series hue
    loc_colour = {"Treated in France": P["series"][0],
                  "Treated abroad": P["series"][1],
                  "Country not declared": NEUTRAL}
    for loc in D.LOCATIONS:
        part = dom[dom["location"] == loc]
        if part.empty:
            continue
        fig.add_bar(y=part.filiere, x=part.share, orientation="h", name=loc,
                    marker=dict(color=loc_colour[loc],
                                line=dict(color=P["surface"], width=2)),
                    hovertemplate="%{y} - " + loc + ": %{x:,.1f} %<extra></extra>")
    fig.update_layout(barmode="stack", xaxis=dict(ticksuffix=" %", range=[0, 100]),
                      yaxis=dict(showgrid=False))
    st.plotly_chart(chart(fig, 120 + 42 * dom.filiere.nunique()), use_container_width=True, theme=None)

# ==========================================================================
# G. territory
# ==========================================================================

st.markdown('<div class="sect">G - Territory</div>', unsafe_allow_html=True)
g_left, g_right = st.columns([7, 5])

with g_left:
    st.subheader(f"Treated tonnage by region, {year}")
    st.caption("Schematic tile map -- every region has equal area, so colour is "
               "not biased by territory size. This is where waste is TREATED, "
               "which tracks industrial capacity, not local collection effort.")
    reg = D.treatment_by_region(trt, codes, year).set_index("region")["masse"]
    if reg.empty:
        st.info(f"No regional treatment data for this selection in {year}.")
    else:
        ncols, nrows = 5, 7
        z = [[None] * ncols for _ in range(nrows)]
        txt = [[""] * ncols for _ in range(nrows)]
        for name, (c, r) in {**D.REGION_TILES,
                             **{k: (c, r + 6) for k, (c, r) in D.DOM_TILES.items()}}.items():
            v = float(reg.get(name, 0))
            z[r][c] = v / 1e3
            txt[r][c] = f"<b>{D.REGION_SHORT.get(name, name[:3].upper())}</b><br>{v/1e3:,.0f}"
        fig = go.Figure(go.Heatmap(
            z=z, text=txt, texttemplate="%{text}",
            textfont=dict(size=11),
            colorscale=[[i / (len(P["sequential"]) - 1), c]
                        for i, c in enumerate(P["sequential"])],
            xgap=4, ygap=4,
            colorbar=dict(title=dict(text="kt", side="right"),
                          thickness=10, outlinewidth=0,
                          tickfont=dict(color=P["text_muted"], size=10)),
            hoverinfo="skip",
        ))
        fig.update_layout(
            yaxis=dict(autorange="reversed", showgrid=False, visible=False),
            xaxis=dict(showgrid=False, visible=False),
        )
        st.plotly_chart(chart(fig, 460), use_container_width=True, theme=None)
        st.caption("Bottom row: overseas regions. Values in kt.")

with g_right:
    st.subheader("Data coverage")
    st.caption("Which filiere x year cells carry treatment declarations at all. "
               "Blank cells are gaps in the extract, not zeros.")
    cov = D.coverage_matrix(trt[trt.filiere.isin(codes)])
    if cov.empty:
        st.info("No treatment data for this selection.")
    else:
        st.dataframe(cov.replace({True: "yes", False: ""}), use_container_width=True)

# ==========================================================================
# caveats
# ==========================================================================

with st.expander("Data caveats -- read before citing anything on this page"):
    st.markdown(
        f"""
**1. There is no collection dataset in `data/raw` yet.** Every rate on this page
is `treated mass / tonnage put on market`, which is a proxy. ADEME's published
collection rates use regulatory formulas with their own scope rules and will not
match. Download *REP - Tonnages issus des lieux de collecte* to close this gap.

**2. `type_ton` codes are alternative accounting bases, not additive.** EMPAP
declares under `TON_SOU`, PMCB under `FIN` and `OPE`, and so on. Summing across
them double-counts. The treatment-mix chart uses the dominant code per filiere;
the headline tiles do not, so treat them as order-of-magnitude only.

**3. `reg_site_trt` uses PRE-2016 region codes** (22 metropolitan regions).
`lib/data.LEGACY_REGION` maps them to the current 13. The mapping is one-way.

**4. Treatment location is not collection location.** A region with high treated
tonnage has treatment plants, not necessarily good collection. Per CLAUDE.md's
granularity rule: the finest level here is `dep_site_trt` (department of the
treatment site). Nothing on this page is municipal.

**5. {len(D._RULES)} prefix rules map 73 `typ_trt` codes to four hierarchy
buckets.** Anything unmatched shows as *Unclassified* rather than being folded
into a bucket. Current unclassified share in this selection:
**{(trt_y.loc[trt_y.bucket == 'Unclassified', 'masse'].sum() / trt_y.masse.sum() * 100) if trt_y.masse.sum() else 0:,.1f} %**.
If that number is large, fix the rules in `lib/data._RULES` before trusting
chart D.

**6. Targets in chart B are placeholders.** See `lib/data.PLACEHOLDER_TARGETS`.
"""
    )
