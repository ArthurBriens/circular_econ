"""
AUTHOR: Arthur Briens
DATE: 19/08/2026

EPR market structure -- France. Monopoly, duopoly, oligopoly.

Every REP filiere is a regulated compliance market. This page asks how many
bodies a producer can actually choose between, how much of the market the
leader holds, and which filieres have opened up or consolidated over time.

Reading order: how many suppliers -> how plural is that really -> what changed
-> who moves across markets -> how goods arrive.

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

from lib import data as D        # noqa: E402
from lib import market as M      # noqa: E402
from lib import theme as T       # noqa: E402

st.set_page_config(page_title="EPR market structure - France", layout="wide")
T.register_templates()

# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------

with st.sidebar:
    st.header("Filters")
    dark = st.toggle("Dark mode", value=False, key="epr_dark")

P = T.palette(dark)
TPL = T.template_name(dark)
NEUTRAL = "#c3c2b7" if not dark else "#52514e"
st.markdown(T.page_css(dark), unsafe_allow_html=True)

D.require_data()

msm = D.load_msm()
actors = D.load_actors()
panel = M.actor_panel(msm, actors)
struct = M.structure(panel)
LATEST = int(struct["annee"].max())

with st.sidebar:
    year = st.select_slider(
        "Snapshot year", options=sorted(struct["annee"].unique()), value=LATEST)
    all_codes = sorted(struct["filiere"].unique())
    codes = st.multiselect(
        "Filiere", options=all_codes, default=all_codes,
        format_func=lambda c: f"{c} - {D.FILIERE_EN.get(c, c)}")

if not codes:
    st.info("Select at least one filiere.")
    st.stop()

struct = struct[struct["filiere"].isin(codes)]
panel = panel[panel["filiere"].isin(codes)]
snap = struct[struct["annee"] == year]

# structure classes are ORDERED, so they wear the ordinal ramp rather than
# categorical hues: monopoly darkest, broad oligopoly lightest
STRUCT_COLOUR = dict(zip(M.STRUCTURES, P["ordinal"]))
RANK_COLOUR = P["ordinal"]      # leader, 2nd, 3rd, remainder


# theme=None plus explicit surfaces: Streamlit merges its own config.toml
# colours over a figure's template defaults, so the template alone loses.
def chart(fig: go.Figure, height: int = 320) -> go.Figure:
    fig.update_layout(
        template=TPL, height=height, margin=dict(l=8, r=8, t=28, b=8),
        paper_bgcolor=P["surface"], plot_bgcolor=P["surface"],
    )
    return fig


def show(fig: go.Figure, height: int = 320) -> None:
    st.plotly_chart(chart(fig, height), use_container_width=True, theme=None)


def cell_text(v, pct: bool = False) -> str:
    """Heatmap cell label.

    Two traps: a NaN must render as an empty cell (Plotly's texttemplate prints
    the literal "NaN" otherwise), and a small but non-zero share must not round
    to "0%" -- a body present with 0.3 % of a filiere is present, and printing
    zero reads as absent.
    """
    if pd.isna(v):
        return ""
    if not pct:
        return f"{v:,.0f}"
    if v == 0:
        return "0%"
    if v < 0.5:
        return "<1%"
    return f"{v:,.0f}%"


st.title("EPR market structure: monopoly, duopoly, oligopoly")
st.caption(
    "Each REP filiere is a market and each declarant a supplier of compliance. "
    "The question is how much choice a producer actually has. Source: ADEME "
    f"SYDEREP put-on-market declarations, read from {D.data_origin()}."
)

if snap.empty:
    st.info(f"No filiere in the current selection reported in {year}.")
    st.stop()

# ==========================================================================
# A. headline
# ==========================================================================

st.markdown('<div class="sect">A - How much choice a producer has</div>',
            unsafe_allow_html=True)

mono = int((snap["structure"] == "Monopoly").sum())
eff_mono = int(snap["effective"].isin(["Sole declarant", "Effective monopoly"]).sum())
contested = int((snap["effective"] == "Contested").sum())
median_cr1 = float(snap["cr1"].median())

k1, k2, k3, k4 = st.columns([1.35, 1, 1, 1])
with k1:
    st.metric(f"Filieres with a single declarant, {year}",
              f"{mono} / {len(snap)}",
              help="A producer in one of these has no choice of compliance "
                   "route beyond running an approved individual system.")
with k2:
    st.metric("Effectively a monopoly", f"{eff_mono} / {len(snap)}",
              help=f"Sole declarant, or a leader holding "
                   f"{M.EFFECTIVE_MONOPOLY:,.0f} % or more.")
with k3:
    st.metric("Median leader share", f"{median_cr1:,.1f} %")
with k4:
    st.metric("Genuinely contested", f"{contested} / {len(snap)}",
              help=f"No declarant holding {M.DOMINANT_SHARE:,.0f} % or more.")

if contested == 0:
    st.caption(
        f"**No filiere in this selection is contested.** In every one, a single "
        f"body holds at least {M.DOMINANT_SHARE:,.0f} % of the tonnage placed on "
        "the market. Counting declarants therefore overstates plurality — which "
        "is what section C is for."
    )

# ==========================================================================
# B. structure map
# ==========================================================================

st.markdown('<div class="sect">B - Market structure, by filiere and year</div>',
            unsafe_allow_html=True)
st.caption(
    "Monopoly = 1 declarant, duopoly = 2, tight oligopoly = 3-4, broad "
    "oligopoly = 5+. Blank means the filiere had not entered the reporting "
    "system that year — not a market with no suppliers. Reading a blank as a "
    "zero is the easiest mistake to make with this dataset."
)

grid = struct.pivot_table(index="filiere", columns="annee",
                          values="structure", aggfunc="first")
zi = grid.map(lambda s: M.STRUCTURES.index(s) if isinstance(s, str) else None)

# discrete colour scale: one flat band per class, so a cell reads as a category
n_cls = len(M.STRUCTURES)
scale = []
for i, c in enumerate(P["ordinal"][:n_cls]):
    scale.append([i / n_cls, c])
    scale.append([(i + 1) / n_cls, c])

fig = go.Figure(go.Heatmap(
    z=zi.values, x=[str(c) for c in grid.columns], y=grid.index,
    # NaN must become an empty string, not be handed to Plotly as a missing
    # value -- texttemplate renders that as the literal "null" in the cell
    text=[["" if not isinstance(v, str) else v for v in row]
          for row in grid.values],
    texttemplate="%{text}",
    textfont=dict(size=10),
    colorscale=scale, zmin=-0.5, zmax=n_cls - 0.5,
    showscale=False, hoverongaps=False, xgap=3, ygap=3,
    hovertemplate="%{y} %{x}<br>%{text}<extra></extra>",
))
fig.update_layout(xaxis=dict(showgrid=False),
                  yaxis=dict(showgrid=False, autorange="reversed"))
show(fig, 110 + 30 * len(grid))

# legend is hand-built: a discrete heatmap has no per-class legend of its own
legend = " &nbsp;&nbsp; ".join(
    f'<span style="display:inline-block;width:10px;height:10px;'
    f'border-radius:2px;background:{STRUCT_COLOUR[s]};"></span> {s}'
    for s in M.STRUCTURES
)
st.markdown(
    f'<div style="font-size:12.5px;color:{P["text_secondary"]};'
    f'margin:-6px 0 4px;">{legend}</div>',
    unsafe_allow_html=True,
)

# ==========================================================================
# C. nominal vs effective
# ==========================================================================

st.markdown('<div class="sect">C - Counting declarants overstates plurality</div>',
            unsafe_allow_html=True)
st.caption(
    f"Each bar splits the filiere between its leader, runner-up, third body and "
    f"the rest, in {year}. A filiere can be a nominal oligopoly and a functional "
    "monopoly at the same time — the bar shows which."
)

c = snap.sort_values("cr1").copy()
c["label"] = c.apply(
    lambda r: f"{r['filiere']} ({r['declarants']})", axis=1)

fig = go.Figure()
segments = [
    ("s1", "Leader", RANK_COLOUR[0]),
    ("s2", "2nd", RANK_COLOUR[1]),
    ("s3", "3rd", RANK_COLOUR[2]),
    ("rest", "All others", RANK_COLOUR[3]),
]
for col, name, colour in segments:
    if c[col].sum() <= 0:
        continue
    fig.add_bar(
        y=c["label"], x=c[col], orientation="h", name=name,
        marker=dict(color=colour, line=dict(color=P["surface"], width=2)),
        customdata=c[["leader", "runner_up", "declarants", "effective"]],
        hovertemplate=("%{y} — " + name + ": %{x:,.1f} %"
                       "<br>Leader: %{customdata[0]}"
                       "<br>Runner-up: %{customdata[1]}"
                       "<br>Declarants: %{customdata[2]}"
                       "<br>Assessed: %{customdata[3]}<extra></extra>"),
    )
fig.add_vline(x=M.DOMINANT_SHARE, line_width=1, line_color=P["text_primary"])
fig.add_annotation(x=M.DOMINANT_SHARE, y=1.02, yref="paper",
                   text=f"{M.DOMINANT_SHARE:,.0f} % — dominance",
                   showarrow=False, xanchor="left", yanchor="bottom",
                   font=dict(size=10, color=P["text_muted"]))
fig.update_layout(barmode="stack", legend=dict(traceorder="normal"),
                  xaxis=dict(ticksuffix=" %", range=[0, 100]),
                  yaxis=dict(showgrid=False))
show(fig, 130 + 30 * len(c))
st.caption("Number in brackets is the declarant count for that filiere.")

# ==========================================================================
# D. what changed
# ==========================================================================

st.markdown('<div class="sect">D - What actually changed</div>',
            unsafe_allow_html=True)

trans = M.transitions(struct)
events = M.entrants_exits(panel)

d_left, d_right = st.columns([6, 6])

with d_left:
    st.subheader("Structure changes")
    if trans.empty:
        st.info("No filiere in this selection changed structure class across "
                "the years it reported.")
    else:
        st.caption(
            f"{len(trans)} change(s) across "
            f"{trans['filiere'].nunique()} filiere(s). Every other filiere held "
            "the same structure for its whole reporting window."
        )
        st.dataframe(
            trans.rename(columns={
                "filiere": "Filiere", "annee": "Year", "from": "From",
                "to": "To", "direction": "Direction",
                "declarants_before": "Before", "declarants_after": "After",
                "cr1_after": "Leader share after (%)"})
            .round(1),
            use_container_width=True, hide_index=True,
        )

with d_right:
    st.subheader("Entries and exits")
    if events.empty:
        st.info("No declarant entered or left mid-window.")
    else:
        st.caption(
            "Only movements INSIDE a filiere's own reporting window count. A "
            "body present in the filiere's first reported year is the incumbent "
            "at the point the record starts, not an entrant."
        )
        fig = go.Figure()
        for i, (ev, colour) in enumerate([("Entry", P["series"][0]),
                                          ("Exit", NEUTRAL)]):
            part = events[events["event"] == ev]
            if part.empty:
                continue
            fig.add_scatter(
                x=part["annee"], y=part["filiere"], mode="markers", name=ev,
                marker=dict(size=12, color=colour,
                            symbol="circle" if ev == "Entry" else "circle-open",
                            line=dict(color=colour, width=2)),
                customdata=part[["name", "share"]],
                hovertemplate=("%{customdata[0]}<br>" + ev + " %{x}"
                               "<br>Share that year: %{customdata[1]:,.1f} %"
                               "<extra></extra>"),
            )
        fig.update_layout(xaxis=dict(dtick=1, showgrid=False),
                          yaxis=dict(showgrid=False, autorange="reversed"))
        show(fig, 110 + 30 * events["filiere"].nunique())

# ==========================================================================
# E. one filiere in detail
# ==========================================================================

st.markdown('<div class="sect">E - Inside one filiere</div>',
            unsafe_allow_html=True)

multi = sorted(struct[struct["declarants"] > 1]["filiere"].unique())
options = multi or codes
default_idx = options.index("EEE") if "EEE" in options else 0
focus = st.selectbox(
    "Filiere in detail", options=options, index=default_idx,
    format_func=lambda c: f"{c} - {D.FILIERE_EN.get(c, c)}",
    help="Only filieres that have had more than one declarant are listed — a "
         "sole-declarant market has no share shift to show.",
)

e_left, e_right = st.columns([7, 5])
fp = panel[panel["filiere"] == focus].sort_values("annee")

with e_left:
    st.subheader(f"Share of tonnage placed on the market — {focus}")
    st.caption("Stacked to 100 %. A band appearing mid-chart is an entrant; a "
               "band ending is an exit from the declaration record.")
    top = (fp.groupby("name")["tonnage"].sum()
             .sort_values(ascending=False).head(8).index.tolist())
    plot = fp.copy()
    plot["grp"] = plot["name"].where(plot["name"].isin(top), "Other")
    agg = plot.groupby(["annee", "grp"], as_index=False)["share"].sum()
    fig = go.Figure()
    order = [n for n in top if n in set(agg["grp"])] + (
        ["Other"] if "Other" in set(agg["grp"]) else [])
    for i, name in enumerate(order):
        part = agg[agg["grp"] == name].sort_values("annee")
        colour = NEUTRAL if name == "Other" else P["series"][i % 8]
        fig.add_bar(
            x=part["annee"], y=part["share"], name=name,
            marker=dict(color=colour, line=dict(color=P["surface"], width=2)),
            hovertemplate=f"{name} %{{x}}<br>%{{y:,.1f}} %<extra></extra>",
        )
    fig.update_layout(barmode="stack", legend=dict(traceorder="normal"),
                      xaxis=dict(dtick=1, showgrid=False),
                      yaxis=dict(ticksuffix=" %", range=[0, 100]))
    show(fig, 360)

    ch = M.churn(panel, focus)
    if not ch.empty:
        peak = ch.loc[ch["churn"].idxmax()]
        st.caption(
            f"Share turnover peaked in {int(peak['annee'])} at "
            f"{peak['churn']:,.1f} points — the share of the market that changed "
            "hands between declarants in a single year."
        )

with e_right:
    st.subheader("Who was active, and when")
    st.caption("Dots mark reported years; a gap in the dots is a gap in the "
               "record. Grey means absent from the latest reported year.")
    act = M.activity(panel)
    act = act[act["filiere"] == focus].sort_values("first_year")
    if act.empty:
        st.info("No declarant history for this filiere.")
    else:
        fig = go.Figure()
        for _, r in act.iterrows():
            alive = r["last_year"] == fp["annee"].max()
            colour = P["series"][0] if alive else NEUTRAL
            nm = r["name"] if len(r["name"]) <= 26 else r["name"][:25] + "…"
            fig.add_scatter(
                x=[r["first_year"], r["last_year"]], y=[nm, nm], mode="lines",
                line=dict(color=colour, width=2), showlegend=False,
                hoverinfo="skip",
            )
            fig.add_scatter(
                x=r["years"], y=[nm] * len(r["years"]), mode="markers",
                marker=dict(size=8, color=colour,
                            line=dict(color=P["surface"], width=2)),
                showlegend=False,
                hovertemplate=f"{r['name']} %{{x}}<extra></extra>",
            )
        fig.update_layout(
            xaxis=dict(dtick=1, showgrid=False,
                       range=[fp["annee"].min() - 0.4, fp["annee"].max() + 0.4]),
            yaxis=dict(showgrid=False, autorange="reversed"),
        )
        show(fig, 110 + 34 * len(act))

# ==========================================================================
# F. multi-market operators
# ==========================================================================

st.markdown('<div class="sect">F - Operators spanning several filieres</div>',
            unsafe_allow_html=True)
st.caption(
    "A body can be one of several declarants in each of many filieres and still "
    f"be the dominant force across all of them. Cell = share of the filiere in "
    f"{year}; blank = not present."
)

pres = M.presence(panel, year)
if pres.empty or "_n" not in pres.columns:
    st.info(f"No declarant data for {year}.")
else:
    span = pres[pres["_n"] > 1].drop(columns=["_n", "_max"])
    if span.empty:
        st.info(f"No declarant operated in more than one filiere in {year}.")
    else:
        span = span.dropna(axis=1, how="all")
        fig = go.Figure(go.Heatmap(
            z=span.values, x=span.columns, y=span.index,
            text=[[cell_text(v, pct=True) for v in row] for row in span.values],
            texttemplate="%{text}", textfont=dict(size=11),
            colorscale=[[i / (len(P["sequential"]) - 1), col]
                        for i, col in enumerate(P["sequential"])],
            xgap=3, ygap=3, hoverongaps=False,
            colorbar=dict(title=dict(text="% of<br>filiere", side="right"),
                          thickness=10, outlinewidth=0,
                          tickfont=dict(color=P["text_muted"], size=10)),
            hovertemplate="%{y} in %{x}: %{z:,.1f} % of the filiere<extra></extra>",
        ))
        fig.update_layout(xaxis=dict(showgrid=False),
                          yaxis=dict(showgrid=False, autorange="reversed"))
        show(fig, 110 + 34 * len(span))

# ==========================================================================
# G. route to market
# ==========================================================================

st.markdown('<div class="sect">G - How product reaches the French market</div>',
            unsafe_allow_html=True)
st.caption(
    f"Producer status on the {focus} declarations, as a share of tonnage. A "
    "supply-chain trend rather than a structural one: whether the goods "
    "entering the market are made in France, imported, or sold in by distance "
    "and marketplace sellers."
)

mix = M.statut_mix(msm, [focus])
if mix.empty or set(mix["family"]) == {"Other / unspecified"}:
    st.info(
        f"{focus} carries no producer-status detail in the extract — the "
        "`statut_prod` field is empty for this filiere. EMPAP, EPRO and MNU are "
        "reported this way; it is an absent field, not a zero."
    )
else:
    fam_colour = {f: P["series"][i] for i, f in enumerate(M.FAMILY_ORDER[:5])}
    fam_colour["Other / unspecified"] = NEUTRAL
    fig = go.Figure()
    for fam in M.FAMILY_ORDER:
        part = mix[mix["family"] == fam].sort_values("annee")
        if part.empty:
            continue
        fig.add_bar(
            x=part["annee"], y=part["share"], name=fam,
            marker=dict(color=fam_colour[fam],
                        line=dict(color=P["surface"], width=2)),
            hovertemplate=f"{fam} %{{x}}<br>%{{y:,.1f}} %<extra></extra>",
        )
    fig.update_layout(barmode="stack", legend=dict(traceorder="normal"),
                      xaxis=dict(dtick=1, showgrid=False),
                      yaxis=dict(ticksuffix=" %", range=[0, 100]))
    show(fig, 340)

    dom = mix[mix["family"] == "Domestic manufacture"].sort_values("annee")
    if len(dom) >= 2:
        delta = dom["share"].iloc[-1] - dom["share"].iloc[0]
        direction = "fallen" if delta < 0 else "risen"
        st.caption(
            f"Domestic manufacture has {direction} {abs(delta):,.1f} points "
            f"since {int(dom['annee'].iloc[0])}, from {dom['share'].iloc[0]:,.1f} % "
            f"to {dom['share'].iloc[-1]:,.1f} % of {focus} tonnage placed on the "
            "market."
        )

# ==========================================================================
# tables and caveats
# ==========================================================================

with st.expander(f"Structure table, {year}"):
    st.dataframe(
        snap.assign(filiere_en=snap["filiere"].map(D.FILIERE_EN))
            [["filiere", "filiere_en", "declarants", "structure", "effective",
              "leader", "cr1", "cr3", "tonnage"]]
            .rename(columns={"filiere": "Code", "filiere_en": "Filiere",
                             "declarants": "Declarants", "structure": "Structure",
                             "effective": "Assessed", "leader": "Leader",
                             "cr1": "Leader share (%)",
                             "cr3": "Top 3 combined (%)",
                             "tonnage": "Tonnage (t)"})
            .sort_values("Leader share (%)", ascending=False).round(1),
        use_container_width=True, hide_index=True,
    )

with st.expander("Method and caveats"):
    st.markdown(
        f"""
**The market definition.** One filiere = one market; each `acteur` in REP.csv is
a supplier of compliance. That mixes eco-organismes with individual systems,
deliberately: an individual system is a genuine alternative to joining a PRO, so
dropping them would overstate concentration.

**Two classifications, on purpose.** *Structure* counts declarants — monopoly 1,
duopoly 2, tight oligopoly 3-4, broad oligopoly 5+. *Assessed* looks at what the
leader holds: a sole declarant, an effective monopoly at
{M.EFFECTIVE_MONOPOLY:,.0f} % or more, a dominant leader at
{M.DOMINANT_SHARE:,.0f} % or more, or contested below that. They disagree, and
the disagreement is the finding — PCHIM has three accredited bodies and a leader
holding essentially all of it. Both thresholds are editorial judgements, not
legal tests, and live in `lib/market.py` as named constants so they are easy to
change or argue with.

**Concentration here is partly by design.** REP markets are built around
accredited bodies, not open entry, so a monopoly filiere is not thereby a
regulatory failure. What the numbers do tell you is how much choice a producer
has, and how exposed a filiere is to a single body's decisions.

**Blank is not zero.** Filieres enter SYDEREP at different dates: PNEU reports
from 2017, EEE from 2019, ABJ from 2023. A filiere with no declarants in a year
had not started reporting. `lib/market.py` only ever returns reported
filiere-years, and every chart renders the rest as blank.

**Entry and exit are measured inside each filiere's own window.** A body present
in the filiere's first reported year is the incumbent at the point the record
begins, not an entrant — filtering against the dataset's overall window instead
of the filiere's would invent a wave of entries in whichever year each filiere
joined the system.

**Entity changes look like entry and exit.** In PNEU the record shows one
declarant ending and a near-identically named one starting the next year at a
similar tonnage — a legal restructuring, not a new competitor. The charts show
the record as it is; check the declarant name before calling any movement a
market event.

**Zero-tonnage rows are dropped** before shares are computed. A body registered
in a filiere but placing nothing on the market is not a supplier that year.

**Route to market is not available everywhere.** `statut_prod` is empty for
EMPAP, EPRO and MNU. Where it exists, PNEU uses its own `Type_A`..`Type_F`
codes, which the referential defines identically to the generic ones; they fold
into the same families in `lib.market.STATUT_FAMILY`.
"""
    )
