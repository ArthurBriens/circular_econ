"""
AUTHOR: Arthur Briens
DATE: 19/08/2026

Market-structure measures over the ADEME put-on-market declarations.

A REP filiere is a regulated compliance market: producers must join an
eco-organisme or run an approved individual system, so the declarants in
REP.csv ARE that market's suppliers of compliance. This module classifies those
markets as monopoly / duopoly / oligopoly and measures how dominant the leader
is inside each one.

TWO CLASSIFICATIONS, DELIBERATELY
---------------------------------
`structure` counts declarants. `effective` looks at what the leader actually
holds. They disagree, and the disagreement is the point: PCHIM has three
accredited declarants and a leader holding essentially the whole market. Calling
that an oligopoly because you can count to three would be wrong; calling it a
monopoly hides that two other bodies are accredited. So both are reported and
the gap between them is treated as the finding.

The thresholds are editorial, not legal. They live here as named constants so
they are easy to argue with and change in one place.

WHAT COUNTS AS THE MARKET
-------------------------
One market = one filiere. Shares are tonnage placed on the market by each
declarant (`acteur`), mixing eco-organismes with individual systems. That is
deliberate: an individual system is a real alternative to joining a PRO, so
excluding them would overstate concentration.

THE COVERAGE TRAP
-----------------
Filieres enter the SYDEREP reporting system at different dates. ABJ first
appears in 2023, EEE in 2019, PNEU in 2017. A filiere with zero declarants in a
year is NOT a market with no suppliers -- it is a market not yet reporting.
Every function here returns only years a filiere actually reported, and the
charts must render the rest as blank, never as zero.

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

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------
# structure classes
#
# Ordered least to most plural. The charts colour them with the ordinal ramp,
# so this order is load-bearing: monopoly darkest, broad oligopoly lightest.
# --------------------------------------------------------------------------

STRUCTURES = ["Monopoly", "Duopoly", "Tight oligopoly", "Broad oligopoly"]

TIGHT_MAX = 4          # 3-4 declarants
DOMINANT_SHARE = 50.0  # leader share at or above which one body sets the terms
EFFECTIVE_MONOPOLY = 95.0  # leader share at which extra declarants are nominal

EFFECTIVE = ["Sole declarant", "Effective monopoly", "Dominant leader", "Contested"]


def classify(n: int) -> str:
    """Nominal structure, from the declarant count alone."""
    if n <= 1:
        return "Monopoly"
    if n == 2:
        return "Duopoly"
    if n <= TIGHT_MAX:
        return "Tight oligopoly"
    return "Broad oligopoly"


def classify_effective(n: int, cr1: float) -> str:
    """Effective structure, from what the leader actually holds.

    "Sole declarant" is kept separate from "Effective monopoly" so a market with
    one accredited body is not conflated with one that has several on paper and
    a leader taking all of it -- the policy question differs.
    """
    if n <= 1:
        return "Sole declarant"
    if cr1 >= EFFECTIVE_MONOPOLY:
        return "Effective monopoly"
    if cr1 >= DOMINANT_SHARE:
        return "Dominant leader"
    return "Contested"


# --------------------------------------------------------------------------
# producer status -> route to market
#
# Type_A..Type_F are PNEU-specific aliases of the generic codes; the referential
# gives them identical libelles, so they fold into the same families.
# --------------------------------------------------------------------------

FAMILY_ORDER = [
    "Domestic manufacture",
    "Import (non-EU)",
    "EU introduction",
    "Distance & marketplace",
    "Reseller / own brand",
    "Other / unspecified",
]

STATUT_FAMILY = {
    "FAB": "Domestic manufacture", "FAB_EXPL": "Domestic manufacture",
    "FAB_PNEU_ENGINS": "Domestic manufacture", "EXPL": "Domestic manufacture",
    "Type_A": "Domestic manufacture", "Type_B": "Domestic manufacture",

    "IMP": "Import (non-EU)", "IMP_ENGINS": "Import (non-EU)",
    "IMP_PNEU_ENGINS": "Import (non-EU)", "Type_C": "Import (non-EU)",
    "Type_D": "Import (non-EU)", "Type_E": "Import (non-EU)",

    "INT": "EU introduction", "INT_VEH": "EU introduction",
    "IMP_INT": "EU introduction",

    "DIS": "Distance & marketplace", "PMH": "Distance & marketplace",

    "REV": "Reseller / own brand", "Type_F": "Reseller / own brand",
    "DON": "Reseller / own brand", "EMBAL": "Reseller / own brand",
}


def family_of(code) -> str:
    if not isinstance(code, str):
        return "Other / unspecified"
    return STATUT_FAMILY.get(code, "Other / unspecified")


# --------------------------------------------------------------------------
# panels
# --------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def actor_panel(msm: pd.DataFrame, actors: pd.DataFrame) -> pd.DataFrame:
    """One row per (filiere, year, declarant) with its tonnage and share.

    Zero-tonnage rows are dropped: a declarant registered but placing nothing on
    the market is not a supplier that year, and keeping it would inflate the
    declarant count and understate the leader's grip.
    """
    g = (msm.groupby(["filiere", "annee", "acteur"], as_index=False)["tonnage"]
            .sum()
            .query("tonnage > 0"))
    names = actors.set_index("Acteur")["raison_sociale"]
    g["name"] = g["acteur"].map(names).fillna(g["acteur"])
    g["share"] = (g["tonnage"]
                  / g.groupby(["filiere", "annee"])["tonnage"].transform("sum") * 100)
    return g


@st.cache_data(show_spinner=False)
def structure(panel: pd.DataFrame) -> pd.DataFrame:
    """Structure class, leader share and top-3 shares per filiere-year."""
    rows = []
    for (fil, yr), grp in panel.groupby(["filiere", "annee"]):
        ranked = grp.sort_values("share", ascending=False)
        shares = ranked["share"].tolist()
        n = len(shares)
        cr1 = shares[0]
        rows.append({
            "filiere": fil,
            "annee": yr,
            "declarants": n,
            "cr1": cr1,
            "cr2": sum(shares[:2]),
            "cr3": sum(shares[:3]),
            "s1": shares[0],
            "s2": shares[1] if n > 1 else 0.0,
            "s3": shares[2] if n > 2 else 0.0,
            "rest": max(0.0, 100.0 - sum(shares[:3])),
            "leader": ranked["name"].iloc[0],
            "runner_up": ranked["name"].iloc[1] if n > 1 else "-",
            "structure": classify(n),
            "effective": classify_effective(n, cr1),
            "tonnage": float(grp["tonnage"].sum()),
        })
    return pd.DataFrame(rows).sort_values(["filiere", "annee"])


@st.cache_data(show_spinner=False)
def transitions(struct: pd.DataFrame) -> pd.DataFrame:
    """Every year a filiere changed structure class, and in which direction.

    `direction` is signed by position in STRUCTURES: opening up (more
    declarants) or consolidating (fewer). A filiere with no row here held the
    same structure across every year it reported.
    """
    rows = []
    for fil, grp in struct.sort_values("annee").groupby("filiere"):
        seq = grp[["annee", "structure", "declarants", "cr1"]].to_dict("records")
        for prev, cur in zip(seq, seq[1:]):
            if cur["structure"] == prev["structure"]:
                continue
            opened = STRUCTURES.index(cur["structure"]) > STRUCTURES.index(prev["structure"])
            rows.append({
                "filiere": fil,
                "annee": cur["annee"],
                "from": prev["structure"],
                "to": cur["structure"],
                "direction": "Opened up" if opened else "Consolidated",
                "declarants_before": prev["declarants"],
                "declarants_after": cur["declarants"],
                "cr1_after": cur["cr1"],
            })
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def entrants_exits(panel: pd.DataFrame) -> pd.DataFrame:
    """Declarants whose first or last reported year is not the filiere's own.

    A declarant appearing in a filiere's first reported year is not an entrant,
    it is the incumbent at the point the record begins -- the same for the last
    year and exits. Filtering on the FILIERE's window rather than the dataset's
    is what keeps those two apart.
    """
    rows = []
    for fil, grp in panel.groupby("filiere"):
        f_first, f_last = grp["annee"].min(), grp["annee"].max()
        for act, sub in grp.groupby("acteur"):
            first, last = sub["annee"].min(), sub["annee"].max()
            if first > f_first:
                rows.append({"filiere": fil, "annee": first, "event": "Entry",
                             "name": sub["name"].iloc[0],
                             "share": float(sub.loc[sub["annee"] == first, "share"].iloc[0])})
            if last < f_last:
                rows.append({"filiere": fil, "annee": last, "event": "Exit",
                             "name": sub["name"].iloc[0],
                             "share": float(sub.loc[sub["annee"] == last, "share"].iloc[0])})
    out = pd.DataFrame(rows)
    return out.sort_values(["annee", "filiere"]) if not out.empty else out


@st.cache_data(show_spinner=False)
def activity(panel: pd.DataFrame) -> pd.DataFrame:
    """Per declarant per filiere: first and last active year, peak share.

    `years` keeps the actual list of active years so a gap (present, absent,
    present again) can be drawn honestly rather than smoothed into one span.
    """
    rows = []
    for (fil, act), grp in panel.groupby(["filiere", "acteur"]):
        yrs = sorted(grp["annee"].unique())
        rows.append({
            "filiere": fil,
            "acteur": act,
            "name": grp["name"].iloc[0],
            "first_year": yrs[0],
            "last_year": yrs[-1],
            "years": yrs,
            "n_years": len(yrs),
            "peak_share": float(grp["share"].max()),
            "last_share": float(grp.sort_values("annee")["share"].iloc[-1]),
        })
    return pd.DataFrame(rows).sort_values(["filiere", "first_year"])


@st.cache_data(show_spinner=False)
def statut_mix(msm: pd.DataFrame, codes: list[str]) -> pd.DataFrame:
    """Share of tonnage by route to market, per year, for the given filieres.

    Aggregating routes ACROSS filieres is meaningless -- PMCB alone is two
    orders of magnitude larger than the rest and would swamp everything -- so
    callers should pass one filiere, or filieres of comparable size.
    """
    sel = msm[msm["filiere"].isin(codes)].copy()
    sel = sel[sel["tonnage"] > 0]
    if sel.empty:
        return sel.assign(family=[], share=[])
    sel["family"] = sel["statut_prod"].map(family_of)
    g = sel.groupby(["annee", "family"], as_index=False)["tonnage"].sum()
    g["share"] = g["tonnage"] / g.groupby("annee")["tonnage"].transform("sum") * 100
    return g


@st.cache_data(show_spinner=False)
def presence(panel: pd.DataFrame, year: int) -> pd.DataFrame:
    """Declarant x filiere share matrix for one year.

    Surfaces the multi-market operators: several eco-organismes are accredited
    across more than one filiere, which is invisible in any single-filiere view.
    """
    sel = panel[panel["annee"] == year]
    if sel.empty:
        return pd.DataFrame()
    m = sel.pivot_table(index="name", columns="filiere", values="share", aggfunc="sum")
    m["_n"] = m.notna().sum(axis=1)
    m["_max"] = m.drop(columns="_n").max(axis=1)
    return m.sort_values(["_n", "_max"], ascending=False)


def churn(panel: pd.DataFrame, filiere: str) -> pd.DataFrame:
    """Year-on-year share turnover: half the sum of absolute share changes.

    Ranges 0 (nothing moved) to 100 (complete turnover). Halved so a transfer of
    x points from one declarant to another counts once, not twice.
    """
    sel = panel[panel["filiere"] == filiere]
    wide = sel.pivot_table(index="annee", columns="acteur", values="share",
                           aggfunc="sum").fillna(0)
    if len(wide) < 2:
        return pd.DataFrame(columns=["annee", "churn"])
    d = wide.diff().abs().sum(axis=1) / 2
    return d.dropna().reset_index(name="churn")
