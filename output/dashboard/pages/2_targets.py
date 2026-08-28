"""
AUTHOR: Arthur Briens
DATE: 19/08/2026

Circularity targets -- France vs Brazil.

Two sections: government targets (EU / national / federal / state) and
sector-specific targets (REP cahiers des charges vs acordos setoriais).

ALL FIGURES ARE PLACEHOLDERS until data/raw/targets_fr_br.csv exists. See
lib/targets.py for the schema and the reasoning behind it.

The governing rule of this page: two countries share an x-axis only when their
targets share a denominator. Where they do not, the page draws them apart and
says why. Percentages that look alike and are not is the failure mode this
whole comparison exists to avoid.

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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import targets as TG      # noqa: E402
from lib import theme as T         # noqa: E402

st.set_page_config(page_title="Targets - France vs Brazil", layout="wide")
T.register_templates()

# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------

with st.sidebar:
    st.header("Filters")
    dark = st.toggle("Dark mode", value=False, key="targets_dark")
    countries = st.multiselect("Country", TG.COUNTRIES, default=TG.COUNTRIES)
    families = st.multiselect(
        "Metric family", TG.METRIC_FAMILIES, default=TG.METRIC_FAMILIES,
        help="Our normalised grouping, not the law's wording. "
             "Editable in lib/targets.METRIC_FAMILIES.",
    )

P = T.palette(dark)
TPL = T.template_name(dark)
NEUTRAL = "#c3c2b7" if not dark else "#52514e"
st.markdown(T.page_css(dark), unsafe_allow_html=True)

# colour follows the entity, always the same slot for the same country
COUNTRY_COLOUR = {TG.FRANCE: P["series"][0], TG.BRAZIL: P["series"][1]}


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


df, source, problems = TG.load_targets()
df = df[df["country"].isin(countries) & df["metric_family"].isin(families)]

st.title("Circularity targets - France vs Brazil")
st.caption(
    "France sets targets through EU directives, the loi AGEC and per-filiere REP "
    "specifications. Brazil sets them through the PNRS framing law, the Planares "
    "national plan, and sectoral reverse-logistics agreements. The two are not "
    "the same instrument type, and this page is built to keep that visible."
)

# --------------------------------------------------------------------------
# provenance banner -- the most important element on the page right now
# --------------------------------------------------------------------------

if problems:
    st.error(
        "**targets_fr_br.csv was found but rejected**, so placeholders are in "
        "use. Fix and reload: " + "; ".join(problems)
    )

if source == "placeholder":
    st.markdown(
        '<div class="caveat"><b>Every number on this page is invented.</b> '
        'Instrument names are real; the values, baselines and horizons are '
        'placeholders so the layout can be reviewed. Drop your in-house file at '
        '<code>data/raw/targets_fr_br.csv</code> and it takes over automatically '
        '- no code change. Use the template button below to get the right '
        'headers.</div>',
        unsafe_allow_html=True,
    )

m1, m2, m3, m4 = st.columns([1.35, 1, 1, 1])
verified = int((df["status"] == "verified").sum()) if len(df) else 0
with m1:
    st.metric("Targets verified against a primary source",
              f"{(verified / len(df) * 100) if len(df) else 0:,.0f} %",
              help="Set a row's `status` to 'verified' in the CSV once you have "
                   "checked it against the instrument itself.")
with m2:
    st.metric("Targets loaded", f"{len(df):,}")
with m3:
    st.metric("Government", f"{int((df.level == TG.GOVERNMENT).sum()):,}")
with m4:
    st.metric("Sector-specific", f"{int((df.level == TG.SECTOR).sum()):,}")

st.download_button(
    "Download CSV template",
    data=TG.template_csv(),
    file_name="targets_fr_br.csv",
    mime="text/csv",
    help="The placeholder set, correctly headed. Overwrite the values, keep the "
         "columns, save to data/raw/.",
)

if df.empty:
    st.info("No targets match the current filters.")
    st.stop()


# --------------------------------------------------------------------------
# shared chart builders
# --------------------------------------------------------------------------

_LABEL_LEFT_MARGIN = 230  # px — must match the char limits below
#   sector: 22 chars × ~7 px = 154 px
#   metric: 30 chars × ~7 px = 210 px  →  add ~20 px padding → 230 px


def label_of(r, sector_limit: int = 22, metric_limit: int = 30) -> str:
    """Two-line row label: sector on the first line, metric on the second."""
    sector = r["sector"]
    if len(sector) > sector_limit:
        sector = sector[: sector_limit - 1] + "…"
    metric = r["metric"]
    if len(metric) > metric_limit:
        metric = metric[: metric_limit - 1] + "…"
    return f"{sector}<br>{metric}"


def horizon_chart(sub, row_px: int = 52):
    """Dumbbell: baseline year -> target year.

    Time is the one axis France and Brazil genuinely share. Even when the
    metrics are incomparable, WHEN a commitment bites is directly comparable,
    so this chart carries no comparability caveat.
    """
    # height is derived AFTER this filter, not from the caller's row count:
    # most rows carry no baseline year, so sizing on the input length spread a
    # handful of dumbbells over thousands of empty pixels
    sub = sub.dropna(subset=["baseline_year", "target_year"]).copy()
    if sub.empty:
        return None
    sub["label"] = sub.apply(label_of, axis=1)
    sub["full_label"] = sub["sector"] + " — " + sub["metric"]
    sub = sub.sort_values("target_year")
    height = 120 + row_px * len(sub)

    fig = go.Figure()
    for _, r in sub.iterrows():
        fig.add_scatter(
            x=[r["baseline_year"], r["target_year"]], y=[r["label"], r["label"]],
            mode="lines", line=dict(color=COUNTRY_COLOUR[r["country"]], width=2),
            showlegend=False, hoverinfo="skip",
        )
    for country in [c for c in TG.COUNTRIES if c in set(sub["country"])]:
        part = sub[sub["country"] == country]
        # hollow marker = baseline, filled = target horizon
        fig.add_scatter(
            x=part["baseline_year"], y=part["label"], mode="markers", showlegend=False,
            marker=dict(size=9, color=P["surface"],
                        line=dict(color=COUNTRY_COLOUR[country], width=2)),
            customdata=part[["full_label"]],
            hovertemplate="%{customdata[0]}<br>Baseline year: %{x:.0f}<extra></extra>",
        )
        fig.add_scatter(
            x=part["target_year"], y=part["label"], mode="markers", name=country,
            marker=dict(size=10, color=COUNTRY_COLOUR[country],
                        line=dict(color=P["surface"], width=2)),
            customdata=part[["full_label"]],
            hovertemplate="%{customdata[0]}<br>Target year: %{x:.0f}<extra></extra>",
        )
    fig.update_layout(xaxis=dict(title="", dtick=5, tickangle=0),
                      yaxis=dict(showgrid=False, autorange="reversed"))
    fig = chart(fig, height)
    fig.update_layout(margin=dict(l=_LABEL_LEFT_MARGIN))
    return fig


def progress_chart(sub, row_px: int = 52):
    """Bullet bars: where the metric stands now, against its own target.

    Each row is scored against ITS OWN target, so no cross-country axis
    comparison is implied -- only 'distance travelled', which is legitimate.
    """
    # percentages ONLY: a count row (1,606 lixoes against a target of 0) or a
    # kg/inhab row on a 0-100 axis blows out the scale and reads as 1,600 %
    sub = sub[sub["unit"] == "%"]
    # same reasoning as horizon_chart: size on the surviving rows
    sub = sub.dropna(subset=["latest_value", "target_value"]).copy()
    if sub.empty:
        return None
    height = 120 + row_px * len(sub)
    sub["lower_better"] = sub["metric_family"].isin(TG.LOWER_IS_BETTER)
    sub["label"] = sub.apply(
        lambda r: ("↓ " if r["lower_better"] else "") + label_of(r), axis=1)
    sub["full_label"] = sub["sector"] + " — " + sub["metric"]
    sub = sub.sort_values("target_year")

    fig = go.Figure()
    fig.add_bar(y=sub["label"], x=[100] * len(sub), orientation="h",
                marker_color=P["track"], hoverinfo="skip", showlegend=False,
                width=0.5)
    for country in [c for c in TG.COUNTRIES if c in set(sub["country"])]:
        part = sub[sub["country"] == country]
        fig.add_bar(
            y=part["label"], x=part["latest_value"], orientation="h", name=country,
            marker_color=COUNTRY_COLOUR[country], width=0.5,
            text=[f"{v:,.0f} %" for v in part["latest_value"]],
            textposition="outside", textfont=dict(color=P["text_primary"], size=12),
            cliponaxis=False,
            customdata=part[["target_value", "target_year", "basis", "full_label"]],
            hovertemplate=("%{customdata[3]}"
                           "<br>Latest: %{x:,.1f} %"
                           "<br>Target: %{customdata[0]:,.1f} %"
                           "<br>By year: %{customdata[1]:.0f}"
                           "<br>Basis: %{customdata[2]}<extra></extra>"),
        )
    # target ticks: colour set explicitly, or the colorway supplies a status hue
    fig.add_scatter(
        x=sub["target_value"], y=sub["label"], mode="markers",
        marker=dict(symbol="line-ns-open", size=24, color=P["text_primary"],
                    line=dict(color=P["text_primary"], width=2)),
        name="Target",
        customdata=sub[["target_year", "basis", "full_label"]],
        hovertemplate=("%{customdata[2]}"
                       "<br><b>Target: %{x:,.1f} %</b>"
                       "<br>By year: %{customdata[0]:.0f}"
                       "<br>Basis: %{customdata[1]}<extra></extra>"),
    )
    fig.update_layout(barmode="overlay",
                      xaxis=dict(range=[0, 120], ticksuffix=" %"),
                      yaxis=dict(showgrid=False, autorange="reversed"))
    fig = chart(fig, height)
    # l: explicit fixed margin so labels aren't clipped (automargin loses to
    #    chart()'s margin.l=8 in Streamlit's iframe context)
    # r: room for "100 %" outside-text labels
    fig.update_layout(margin=dict(l=_LABEL_LEFT_MARGIN, r=52))
    return fig


# ==========================================================================
# SECTION 1 -- GOVERNMENT TARGETS
# ==========================================================================

st.markdown('<div class="sect">1 - Government targets</div>', unsafe_allow_html=True)
st.caption(
    "France: EU directives transposed nationally, plus the loi AGEC, plus "
    "regional PRPGD plans. Brazil: the PNRS framing law, the Planares national "
    "plan, and state PERS plans."
)

gov = df[df["level"] == TG.GOVERNMENT]
if gov.empty:
    st.info("No government targets match the current filters.")
else:
    # full width, stacked rather than side by side: these y labels are long, and
    # Plotly reserves left margin for the longest one, so in a half-width column
    # the plot area collapses and the outside value labels get clipped
    st.subheader("What date ate commitments set for")
    st.caption("Hollow marker = baseline year, filled = target year. Time is "
               "the one axis both countries genuinely share, so this chart "
               "needs no comparability caveat.")
    fig = horizon_chart(gov)
    if fig:
        st.plotly_chart(fig, use_container_width=True, theme=None)
        drawn = int(gov[["baseline_year", "target_year"]].notna().all(axis=1).sum())
        st.caption(f"{drawn} of {len(gov)} government targets carry both a "
                   "baseline year and a target year; the rest are rates rather "
                   "than changes and cannot be drawn on a time axis.")

    st.subheader("Distance still to travel")
    st.caption("Each bar is scored against its own target only, so no "
               "cross-country axis comparison is implied. A down-arrow marks "
               "metrics where a LOWER value is the better outcome.")
    fig = progress_chart(gov)
    if fig:
        st.plotly_chart(fig, use_container_width=True, theme=None)
        drawn = int((gov["unit"].eq("%")
                     & gov[["latest_value", "target_value"]].notna().all(axis=1)).sum())
        st.caption(f"{drawn} of {len(gov)} government targets are expressed as a "
                   "percentage AND have a published latest measured value to "
                   "score against. Count-based targets (municipalities, MW) are "
                   "in the table below instead.")

    st.markdown("**What each target actually counts**")
    st.caption("The denominator is where a France/Brazil comparison lives or "
               "dies. Read this before quoting any pair of numbers together.")
    st.dataframe(
        gov[["country", "tier", "metric", "basis", "unit",
             "target_value", "target_year", "instrument", "comparable"]]
        .rename(columns={"country": "Country", "tier": "Tier", "metric": "Metric",
                         "basis": "Basis (denominator)", "unit": "Unit",
                         "target_value": "Target", "target_year": "By",
                         "instrument": "Instrument",
                         "comparable": "Shared basis"}),
        use_container_width=True, hide_index=True,
    )

# ==========================================================================
# SECTION 2 -- SECTOR-SPECIFIC TARGETS
# ==========================================================================

st.markdown('<div class="sect">2 - Sector-specific targets</div>',
            unsafe_allow_html=True)
st.caption(
    "France: per-filiere obligations in each eco-organism's cahier des charges, "
    "market-wide and mandatory. Brazil: acordos setoriais and termos de "
    "compromisso, which bind SIGNATORY firms rather than the whole market. That "
    "difference is structural and survives any amount of data cleaning."
)

sec = df[df["level"] == TG.SECTOR]
if sec.empty:
    st.info("No sector targets match the current filters.")
else:
    s1, s2 = st.columns([7, 5])

    with s1:
        st.subheader("Where both countries set a target for the same sector")
        pairs = TG.paired(df, TG.SECTOR)
        if pairs.empty:
            st.info("No sector has a target on both sides under the current "
                    "filters. That absence is itself a finding - note it rather "
                    "than widening the filters until something appears.")
        else:
            mismatched = int((~pairs["same_basis"]).sum())
            cross = int(pairs.get("cross_family", pd.Series(dtype=bool)).sum())
            if mismatched:
                st.caption(
                    f"{mismatched} of {len(pairs)} pairs do NOT share a "
                    "denominator and are marked `≠`. Their bars sit on one axis "
                    "for convenience of reading, not because the numbers mean "
                    "the same thing."
                )
            if cross:
                st.caption(
                    f"**{cross} of {len(pairs)} go further: the two countries do "
                    "not even measure the same quantity** for that sector, so "
                    "there is no shared metric family to pair on. Those are "
                    "marked `⚠`. Read them as 'both regulate this sector', never "
                    "as 'one is ahead'."
                )
            pairs = pairs.sort_values(
                ["cross_family", "same_basis"], ascending=[True, False]).copy()

            def _prefix(r) -> str:
                if r.get("cross_family"):
                    return "⚠ "
                return "" if r["same_basis"] else "≠ "

            pairs["label"] = pairs.apply(lambda r: _prefix(r) + r["sector"], axis=1)
            fig = go.Figure()
            for country in TG.COUNTRIES:
                col = f"target_value__{country}"
                if col not in pairs.columns:
                    continue
                # each side keeps its OWN metric and basis in the hover -- that
                # difference is the finding, so it must not be flattened away
                extra = pairs[[f"target_year__{country}",
                               f"metric_family__{country}",
                               f"basis__{country}"]]
                fig.add_bar(
                    y=pairs["label"], x=pairs[col], orientation="h", name=country,
                    marker=dict(color=COUNTRY_COLOUR[country],
                                line=dict(color=P["surface"], width=2)),
                    customdata=extra,
                    hovertemplate=("<b>%{y} - " + country + "</b>"
                                   "<br>Target: %{x:,.1f} % by %{customdata[0]:.0f}"
                                   "<br>Measures: %{customdata[1]}"
                                   "<br>Basis: %{customdata[2]}<extra></extra>"),
                )
            fig.update_layout(barmode="group", bargroupgap=0.08,
                              xaxis=dict(ticksuffix=" %"),
                              yaxis=dict(showgrid=False, autorange="reversed"))
            st.plotly_chart(chart(fig, 110 + 56 * len(pairs)),
                            use_container_width=True, theme=None)
            st.caption(
                "`≠` = different denominator. `⚠` = different quantity entirely, "
                "with no shared metric family. Hover a bar to see what each side "
                "actually counts."
            )
            st.dataframe(
                pairs[["sector", f"metric_family__{TG.FRANCE}",
                       f"metric_family__{TG.BRAZIL}", "same_basis", "cross_family"]]
                .rename(columns={"sector": "Sector",
                                 f"metric_family__{TG.FRANCE}": "France measures",
                                 f"metric_family__{TG.BRAZIL}": "Brazil measures",
                                 "same_basis": "Shared basis",
                                 "cross_family": "Different quantity"}),
                use_container_width=True, hide_index=True,
            )

    with s2:
        st.subheader("Which sectors are covered at all")
        st.caption("The structural asymmetry: France runs ~19 REP filieres; "
                   "Brazil's reverse-logistics chains are fewer and narrower. "
                   "An empty cell means no instrument, not missing data.")
        cov = TG.coverage(df)
        if cov.empty:
            st.info("No sector coverage under the current filters.")
        else:
            fig = go.Figure()
            for country in TG.COUNTRIES:
                if country not in cov.columns:
                    continue
                present = cov[cov[country] > 0]
                absent = cov[cov[country] == 0]
                fig.add_scatter(
                    x=[country] * len(present), y=present.index, mode="markers",
                    name=country,
                    marker=dict(size=15, symbol="square",
                                color=COUNTRY_COLOUR[country],
                                line=dict(color=P["surface"], width=2)),
                    customdata=present[[country]],
                    hovertemplate="%{y} - " + country
                                  + ": %{customdata[0]} target(s)<extra></extra>",
                )
                fig.add_scatter(
                    x=[country] * len(absent), y=absent.index, mode="markers",
                    showlegend=False,
                    marker=dict(size=15, symbol="square-open",
                                color=NEUTRAL, line=dict(color=NEUTRAL, width=1.5)),
                    hovertemplate="%{y} - " + country
                                  + ": no target<extra></extra>",
                )
            fig.update_layout(
                xaxis=dict(showgrid=False, categoryorder="array",
                           categoryarray=TG.COUNTRIES),
                yaxis=dict(showgrid=False, autorange="reversed"),
                showlegend=False,
            )
            st.plotly_chart(chart(fig, 90 + 34 * len(cov)), use_container_width=True, theme=None)

    st.markdown("**Sector target detail**")
    st.dataframe(
        sec[["country", "sector", "metric", "basis", "unit", "latest_value",
             "target_value", "target_year", "instrument", "comparable", "note"]]
        .rename(columns={"country": "Country", "sector": "Sector",
                         "metric": "Metric", "basis": "Basis (denominator)",
                         "unit": "Unit", "latest_value": "Latest",
                         "target_value": "Target", "target_year": "By",
                         "instrument": "Instrument", "comparable": "Shared basis",
                         "note": "Note"}),
        use_container_width=True, hide_index=True,
    )

# ==========================================================================
# method
# ==========================================================================

with st.expander("Method and its limits"):
    st.markdown(
        """
**The comparison problem.** France's targets are mostly EU-derived, expressed
as a share of arisings, and binding on the whole market through REP. Brazil's
are set nationally by Planares and sectorally by agreements that bind signatory
firms. A French filiere rate and a Brazilian reverse-logistics rate can both be
"38 %" and mean materially different things, because the denominators differ:
everything placed on the market, versus everything placed on the market *by the
firms that signed*.

**How this page handles it.** Every row carries a `basis` string and a
`comparable` flag. Two countries share an axis only where both are marked
comparable and their basis strings match; otherwise the pair is drawn with a
diamond prefix and the mismatch is stated. The `metric_family` grouping is our
editorial judgement, not a legal category - it is the most contestable thing
here and lives in `lib/targets.METRIC_FAMILIES` so it is easy to argue with.

**Direction.** Landfill metrics improve as they fall. Those families are listed
in `LOWER_IS_BETTER` and prefixed with `v` so a short bar is not misread as
poor performance.

**Asymmetries that are findings, not gaps.** Brazil has targets for open-dump
elimination and universal collection coverage; France has no counterpart
because its baseline already assumes engineered landfill and universal service.
Leave those rows unpaired rather than inventing a French equivalent.

**Replacing the placeholders.** Fill `data/raw/targets_fr_br.csv` using the
template button above. Set `status` to `verified` per row as you check each one
against the instrument itself; the meter at the top tracks how far that has got.
A malformed file is rejected wholesale with the reason shown, rather than
half-loading.
"""
    )
