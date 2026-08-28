"""
AUTHOR: Arthur Briens
DATE: 19/08/2026

France / Brazil circularity targets -- schema, placeholder set, and loader.

THE POINT OF THIS MODULE IS THE SCHEMA, NOT THE NUMBERS.

Every value below is a PLACEHOLDER. They exist so the page can be laid out and
argued about before the real figures arrive. Drop a CSV at

    data/raw/targets_fr_br.csv

with the columns in COLUMNS and it silently takes over -- no code change. Use
the "Download CSV template" button on the page to get a correctly-headed file.

WHY THE SCHEMA LOOKS LIKE THIS
------------------------------
France and Brazil do not set targets on the same footing, and the single
biggest way to produce a misleading comparison is to put two percentages on one
axis when their denominators differ.

    France  : EU directives (Waste Framework, Packaging) transposed into
              national law, plus the loi AGEC, plus per-filiere REP targets set
              in each eco-organism's cahier des charges.
    Brazil  : the PNRS (Lei 12.305/2010) as the framing law, Planares
              (Decreto 11.043/2022) for national targets, and *acordos
              setoriais* / *termos de compromisso* for reverse-logistics
              chains.

So each row carries BOTH a verbatim `metric` (as the instrument words it) and a
normalised `metric_family` (how we choose to group it), plus an explicit
`basis` string and a `comparable` flag. Charts may only put two countries on a
shared axis when `comparable` is True; everything else is drawn side by side
with the mismatch marked. `metric_family` is our editorial judgement, not the
law's -- it is the honest place for the comparison to be contestable.

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

from pathlib import Path

import pandas as pd
import streamlit as st

from . import data as _data


_TRUE = {"true", "yes", "y", "1", "oui", "sim", "vrai"}
_FALSE = {"false", "no", "n", "0", "non", "nao", "não", "faux", ""}


def _truthy(value) -> bool:
    """Parse a spreadsheet boolean without the astype(bool) trap.

    `Series.astype(bool)` on a text column makes EVERY non-empty string True --
    including the literal "false". One stray "n/a" in the column is enough to
    turn the whole thing into strings and silently mark every row comparable,
    which would put mismatched denominators on a shared axis. So parse the text
    explicitly and treat anything unrecognised as False, the safe direction.
    """
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    text = str(value).strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    return False

ROOT = Path(__file__).resolve().parents[3]

# The file is optional and resolved the same way as the ADEME extracts: local
# data/raw first, then a URL in st.secrets["data"]["targets_url"]. Absence is a
# normal state -- the page falls back to the placeholder set below.
TARGETS_FILENAME = "targets_fr_br.csv"
TARGETS_SECRET = "targets_url"

FRANCE, BRAZIL = "France", "Brazil"
COUNTRIES = [FRANCE, BRAZIL]

GOVERNMENT, SECTOR = "government", "sector"

COLUMNS = [
    "country",         # France | Brazil
    "level",           # government | sector
    "tier",            # EU | National | Regional | Federal | State | Sector agreement
    "sector",          # "All municipal waste", "Packaging", "EEE", ...
    "metric_family",   # normalised grouping used for cross-country pairing
    "metric",          # the metric as the instrument words it
    "basis",           # the denominator, in plain words -- the comparability crux
    "unit",            # % | Mt | kg/cap | count | year
    "baseline_value",
    "baseline_year",
    "latest_value",
    "latest_year",
    "target_value",
    "target_year",
    "instrument",      # legal instrument / agreement
    "comparable",      # bool: shares a basis with the other country's same family
    "status",          # placeholder | sourced | verified
    "note",
    "source_url",      # where the figure came from
]

# status values, weakest to strongest:
#   placeholder -- invented, for layout only
#   sourced     -- from a real instrument and cited, but not read in the
#                  primary legal text (secondary source, or a transcription)
#   verified    -- read in the instrument's own text or on the regulator's
#                  official page
# Only `verified` counts towards the meter on the page.
STATUSES = ["placeholder", "sourced", "verified"]

# normalised families, ordered from most to least cross-comparable
METRIC_FAMILIES = [
    "Recycling rate",
    "Separate collection rate",
    "Landfill diversion",
    "Collection coverage",
    "Reuse & preparation for reuse",
    "Reverse-logistics recovery",
]


def _row(**kw) -> dict:
    """Row factory. Defaults keep the placeholder set readable."""
    base = {c: None for c in COLUMNS}
    base.update({"comparable": False, "status": "placeholder", "note": ""})
    base.update(kw)
    return base


# --------------------------------------------------------------------------
# PLACEHOLDER DATA
#
# Instrument names are real; every NUMBER is invented. Do not cite anything
# from this block. Replace via data/raw/targets_fr_br.csv.
# --------------------------------------------------------------------------

_PLACEHOLDER_ROWS = [
    # ---------------- FRANCE, government ----------------
    _row(country=FRANCE, level=GOVERNMENT, tier="EU", sector="All municipal waste",
         metric_family="Recycling rate",
         metric="Preparation for reuse and recycling of municipal waste",
         basis="Total municipal waste generated",
         unit="%", baseline_value=42.0, baseline_year=2015,
         latest_value=49.0, latest_year=2023,
         target_value=55.0, target_year=2025,
         instrument="EU Waste Framework Directive (placeholder value)",
         comparable=True,
         note="PLACEHOLDER. EU has a real staged target series here - verify."),
    _row(country=FRANCE, level=GOVERNMENT, tier="EU", sector="All municipal waste",
         metric_family="Recycling rate",
         metric="Preparation for reuse and recycling of municipal waste",
         basis="Total municipal waste generated",
         unit="%", baseline_value=42.0, baseline_year=2015,
         latest_value=49.0, latest_year=2023,
         target_value=65.0, target_year=2035,
         instrument="EU Waste Framework Directive (placeholder value)",
         comparable=True, note="PLACEHOLDER."),
    _row(country=FRANCE, level=GOVERNMENT, tier="EU", sector="All municipal waste",
         metric_family="Landfill diversion",
         metric="Municipal waste landfilled",
         basis="Total municipal waste generated",
         unit="%", baseline_value=26.0, baseline_year=2015,
         latest_value=17.0, latest_year=2023,
         target_value=10.0, target_year=2035,
         instrument="EU Landfill Directive (placeholder value)",
         comparable=True, note="PLACEHOLDER. Lower is better - see LOWER_IS_BETTER."),
    _row(country=FRANCE, level=GOVERNMENT, tier="National", sector="All non-hazardous waste",
         metric_family="Landfill diversion",
         metric="Reduction in non-hazardous waste landfilled vs 2010",
         basis="2010 landfilled tonnage",
         unit="%", baseline_value=0.0, baseline_year=2010,
         latest_value=38.0, latest_year=2023,
         target_value=50.0, target_year=2025,
         instrument="Loi AGEC (placeholder value)",
         comparable=False,
         note="PLACEHOLDER. Basis is a 2010 index, not a share of arisings - "
              "not comparable with the EU landfill rate above."),
    _row(country=FRANCE, level=GOVERNMENT, tier="National", sector="All municipal waste",
         metric_family="Reuse & preparation for reuse",
         metric="Share of household waste reused or prepared for reuse",
         basis="Total household waste",
         unit="%", baseline_value=1.0, baseline_year=2019,
         latest_value=2.0, latest_year=2023,
         target_value=5.0, target_year=2030,
         instrument="Loi AGEC (placeholder value)",
         comparable=True, note="PLACEHOLDER."),
    _row(country=FRANCE, level=GOVERNMENT, tier="Regional", sector="All waste",
         metric_family="Landfill diversion",
         metric="Regional cap on landfill capacity",
         basis="Regional plan ceiling",
         unit="%", baseline_value=100.0, baseline_year=2010,
         latest_value=72.0, latest_year=2023,
         target_value=50.0, target_year=2031,
         instrument="PRPGD regional plans (placeholder value)",
         comparable=False,
         note="PLACEHOLDER. Set per region; a national figure is an aggregation "
              "choice, not a legal target."),

    # ---------------- BRAZIL, government ----------------
    _row(country=BRAZIL, level=GOVERNMENT, tier="Federal", sector="All municipal waste",
         metric_family="Recycling rate",
         metric="Recovery of recyclable material from municipal solid waste",
         basis="Total municipal solid waste generated",
         unit="%", baseline_value=4.0, baseline_year=2020,
         latest_value=6.0, latest_year=2023,
         target_value=20.0, target_year=2031,
         instrument="Planares / Decreto 11.043-2022 (placeholder value)",
         comparable=True,
         note="PLACEHOLDER. Planares does publish a staged recycling series to "
              "2040 - seed the real numbers here first."),
    _row(country=BRAZIL, level=GOVERNMENT, tier="Federal", sector="All municipal waste",
         metric_family="Recycling rate",
         metric="Recovery of recyclable material from municipal solid waste",
         basis="Total municipal solid waste generated",
         unit="%", baseline_value=4.0, baseline_year=2020,
         latest_value=6.0, latest_year=2023,
         target_value=48.0, target_year=2040,
         instrument="Planares / Decreto 11.043-2022 (placeholder value)",
         comparable=True, note="PLACEHOLDER."),
    _row(country=BRAZIL, level=GOVERNMENT, tier="Federal", sector="All municipal waste",
         metric_family="Landfill diversion",
         metric="Waste sent to open dumps and irregular sites",
         basis="Total municipal solid waste collected",
         unit="%", baseline_value=39.0, baseline_year=2020,
         latest_value=32.0, latest_year=2023,
         target_value=0.0, target_year=2031,
         instrument="PNRS / Lei 12.305-2010 (placeholder value)",
         comparable=False,
         note="PLACEHOLDER. 'Open dump elimination' has no French equivalent - "
              "France's baseline already assumes engineered landfill."),
    _row(country=BRAZIL, level=GOVERNMENT, tier="Federal", sector="All municipal waste",
         metric_family="Separate collection rate",
         metric="Municipalities operating selective collection",
         basis="Count of municipalities (5,570)",
         unit="%", baseline_value=38.0, baseline_year=2020,
         latest_value=44.0, latest_year=2023,
         target_value=70.0, target_year=2031,
         instrument="Planares (placeholder value)",
         comparable=False,
         note="PLACEHOLDER. Denominator is MUNICIPALITIES, not tonnes or people. "
              "Never place on one axis with a tonnage-based French rate."),
    _row(country=BRAZIL, level=GOVERNMENT, tier="Federal", sector="All municipal waste",
         metric_family="Collection coverage",
         metric="Population served by regular waste collection",
         basis="Total population",
         unit="%", baseline_value=92.0, baseline_year=2020,
         latest_value=94.0, latest_year=2023,
         target_value=100.0, target_year=2033,
         instrument="Planares (placeholder value)",
         comparable=False,
         note="PLACEHOLDER. France is at universal coverage, so this target has "
              "no French counterpart - an asymmetry, not a data gap."),
    _row(country=BRAZIL, level=GOVERNMENT, tier="State", sector="All municipal waste",
         metric_family="Recycling rate",
         metric="State recovery target",
         basis="State municipal solid waste generated",
         unit="%", baseline_value=5.0, baseline_year=2020,
         latest_value=8.0, latest_year=2023,
         target_value=25.0, target_year=2035,
         instrument="State PERS plans (placeholder value)",
         comparable=False,
         note="PLACEHOLDER. State plans vary widely; one row cannot stand for all 27."),

    # ---------------- FRANCE, sector (REP filieres) ----------------
    _row(country=FRANCE, level=SECTOR, tier="Sector agreement", sector="Packaging",
         metric_family="Recycling rate", metric="Household packaging recycling rate",
         basis="Packaging placed on market",
         unit="%", baseline_value=65.0, baseline_year=2018,
         latest_value=72.0, latest_year=2024,
         target_value=80.0, target_year=2030,
         instrument="REP EMPAP cahier des charges (placeholder value)",
         comparable=True, note="PLACEHOLDER."),
    _row(country=FRANCE, level=SECTOR, tier="Sector agreement", sector="EEE",
         metric_family="Separate collection rate", metric="EEE collection rate",
         basis="EEE placed on market, 3-year average",
         unit="%", baseline_value=42.0, baseline_year=2018,
         latest_value=48.0, latest_year=2024,
         target_value=65.0, target_year=2030,
         instrument="REP EEE cahier des charges (placeholder value)",
         comparable=True, note="PLACEHOLDER."),
    _row(country=FRANCE, level=SECTOR, tier="Sector agreement", sector="Textiles",
         metric_family="Separate collection rate", metric="TLC collection rate",
         basis="Textiles placed on market",
         unit="%", baseline_value=26.0, baseline_year=2018,
         latest_value=37.0, latest_year=2024,
         target_value=60.0, target_year=2030,
         instrument="REP TLC cahier des charges (placeholder value)",
         comparable=True, note="PLACEHOLDER."),
    _row(country=FRANCE, level=SECTOR, tier="Sector agreement", sector="Furniture",
         metric_family="Recycling rate", metric="Furniture recycling rate",
         basis="Furniture collected",
         unit="%", baseline_value=45.0, baseline_year=2018,
         latest_value=55.0, latest_year=2024,
         target_value=70.0, target_year=2030,
         instrument="REP EA cahier des charges (placeholder value)",
         comparable=True, note="PLACEHOLDER."),
    _row(country=FRANCE, level=SECTOR, tier="Sector agreement", sector="Tyres",
         metric_family="Recycling rate", metric="Tyre recovery rate",
         basis="Tyres placed on market",
         unit="%", baseline_value=88.0, baseline_year=2018,
         latest_value=91.0, latest_year=2024,
         target_value=95.0, target_year=2030,
         instrument="REP PNEU cahier des charges (placeholder value)",
         comparable=True, note="PLACEHOLDER."),
    _row(country=FRANCE, level=SECTOR, tier="Sector agreement", sector="Batteries",
         metric_family="Separate collection rate", metric="Portable battery collection rate",
         basis="Batteries placed on market",
         unit="%", baseline_value=45.0, baseline_year=2018,
         latest_value=50.0, latest_year=2024,
         target_value=63.0, target_year=2027,
         instrument="REP BAT cahier des charges (placeholder value)",
         comparable=True, note="PLACEHOLDER."),
    _row(country=FRANCE, level=SECTOR, tier="Sector agreement", sector="Textiles",
         metric_family="Reuse & preparation for reuse", metric="Textiles reused",
         basis="Textiles collected",
         unit="%", baseline_value=8.0, baseline_year=2018,
         latest_value=14.0, latest_year=2024,
         target_value=25.0, target_year=2030,
         instrument="REP TLC cahier des charges (placeholder value)",
         comparable=True, note="PLACEHOLDER."),

    # ---------------- BRAZIL, sector (logistica reversa) ----------------
    _row(country=BRAZIL, level=SECTOR, tier="Sector agreement", sector="Packaging",
         metric_family="Reverse-logistics recovery",
         metric="Packaging recovered through reverse logistics",
         basis="Packaging placed on market by signatory firms",
         unit="%", baseline_value=22.0, baseline_year=2018,
         latest_value=30.0, latest_year=2024,
         target_value=50.0, target_year=2031,
         instrument="Acordo Setorial de Embalagens em Geral (placeholder value)",
         comparable=False,
         note="PLACEHOLDER. Denominator covers SIGNATORY firms only, not the "
              "whole market - structurally narrower than the French REP basis."),
    _row(country=BRAZIL, level=SECTOR, tier="Sector agreement", sector="EEE",
         metric_family="Reverse-logistics recovery",
         metric="Electro-electronic products collected",
         basis="Products placed on market by signatory firms",
         unit="%", baseline_value=6.0, baseline_year=2020,
         latest_value=12.0, latest_year=2024,
         target_value=25.0, target_year=2031,
         instrument="Acordo Setorial de Eletroeletronicos (placeholder value)",
         comparable=False, note="PLACEHOLDER. Signatory-firm basis."),
    _row(country=BRAZIL, level=SECTOR, tier="Sector agreement", sector="EEE",
         metric_family="Collection coverage",
         metric="Municipalities with an EEE drop-off point",
         basis="Count of municipalities above 80,000 inhabitants",
         unit="%", baseline_value=15.0, baseline_year=2020,
         latest_value=34.0, latest_year=2024,
         target_value=100.0, target_year=2030,
         instrument="Acordo Setorial de Eletroeletronicos (placeholder value)",
         comparable=False,
         note="PLACEHOLDER. Infrastructure-presence target, not a recovery rate."),
    _row(country=BRAZIL, level=SECTOR, tier="Sector agreement", sector="Tyres",
         metric_family="Reverse-logistics recovery", metric="Tyres collected and destined",
         basis="Tyres placed on market",
         unit="%", baseline_value=85.0, baseline_year=2018,
         latest_value=92.0, latest_year=2024,
         target_value=100.0, target_year=2030,
         instrument="CONAMA tyre resolution (placeholder value)",
         comparable=True,
         note="PLACEHOLDER. Tyres are the closest to a like-for-like pair with "
              "France - same basis, mandatory, market-wide."),
    _row(country=BRAZIL, level=SECTOR, tier="Sector agreement", sector="Batteries",
         metric_family="Reverse-logistics recovery", metric="Batteries collected",
         basis="Batteries placed on market by signatory firms",
         unit="%", baseline_value=20.0, baseline_year=2018,
         latest_value=28.0, latest_year=2024,
         target_value=45.0, target_year=2031,
         instrument="Acordo Setorial de Pilhas e Baterias (placeholder value)",
         comparable=False, note="PLACEHOLDER. Signatory-firm basis."),
    _row(country=BRAZIL, level=SECTOR, tier="Sector agreement", sector="Lubricant oils",
         metric_family="Reverse-logistics recovery", metric="Used lubricant oil collected",
         basis="Lubricant oil placed on market",
         unit="%", baseline_value=38.0, baseline_year=2018,
         latest_value=44.0, latest_year=2024,
         target_value=55.0, target_year=2030,
         instrument="CONAMA lubricant resolution (placeholder value)",
         comparable=True, note="PLACEHOLDER."),
    _row(country=BRAZIL, level=SECTOR, tier="Sector agreement", sector="Medicines",
         metric_family="Reverse-logistics recovery", metric="Pharmacies with a collection point",
         basis="Count of pharmacies in scope",
         unit="%", baseline_value=10.0, baseline_year=2021,
         latest_value=26.0, latest_year=2024,
         target_value=60.0, target_year=2030,
         instrument="Decreto 10.388-2020 (placeholder value)",
         comparable=False, note="PLACEHOLDER. Infrastructure-presence target."),
]

# families where a LOWER number is the better outcome -- charts must not read
# "short bar = failing" for these
LOWER_IS_BETTER = {"Landfill diversion"}


def _placeholder_frame() -> pd.DataFrame:
    return pd.DataFrame(_PLACEHOLDER_ROWS, columns=COLUMNS)


def template_csv() -> str:
    """The placeholder set as CSV -- the starting point for the real file."""
    return _placeholder_frame().to_csv(index=False)


@st.cache_data(show_spinner=False)
def load_targets() -> tuple[pd.DataFrame, str, list[str]]:
    """Return (frame, source, problems).

    `source` is "file" when data/raw/targets_fr_br.csv was used and
    "placeholder" otherwise. `problems` lists schema complaints about the file;
    if there are any, the placeholder set is used instead, so a malformed CSV
    degrades loudly rather than half-loading.
    """
    handle = _data.resolve_optional(TARGETS_FILENAME, TARGETS_SECRET)
    if handle is None:
        return _placeholder_frame(), "placeholder", []

    df = pd.read_csv(handle)
    problems: list[str] = []

    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        problems.append(f"missing columns: {', '.join(missing)}")

    if not problems:
        bad_country = sorted(set(df["country"].dropna()) - set(COUNTRIES))
        if bad_country:
            problems.append(f"unexpected country values: {', '.join(bad_country)}")
        bad_level = sorted(set(df["level"].dropna()) - {GOVERNMENT, SECTOR})
        if bad_level:
            problems.append(f"unexpected level values: {', '.join(bad_level)}")

    if problems:
        return _placeholder_frame(), "placeholder", problems

    df["comparable"] = df["comparable"].map(_truthy)
    for c in ("baseline_value", "latest_value", "target_value",
              "baseline_year", "latest_year", "target_year"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[COLUMNS], "file", []


# --------------------------------------------------------------------------
# pairing
# --------------------------------------------------------------------------

def paired(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """One row per SECTOR that both countries set a percentage target for.

    Pairing is on `sector` alone, deliberately NOT on (sector, metric_family).
    France measures packaging as a recycling rate and Brazil measures it as
    reverse-logistics recovery, so keying on both fields matches nothing and the
    chart comes up empty -- which hides the very comparison the page is for.

    WHICH row represents a sector matters. Taking the furthest-horizon row
    regardless of family produced nonsense pairs: France's longest-dated EEE
    target is a 2 % reuse obligation, which is not the thing to set beside
    Brazil's 17 % collection target. So:

      1. if the two countries share a metric_family for that sector, restrict
         to it and take the furthest horizon within it -- the closest to
         like-for-like the data allows;
      2. otherwise fall back to the furthest horizon overall and set
         `cross_family`, so the chart can say the two bars measure different
         things. That is a stronger warning than a basis mismatch: the
         denominators differ AND so does the quantity being counted.
    """
    sel = df[(df["level"] == level) & (df["unit"] == "%")].copy()
    if sel.empty:
        return sel.head(0)

    keep = []
    cross = {}
    for sector, grp in sel.groupby("sector"):
        fams = {c: set(g["metric_family"].dropna())
                for c, g in grp.groupby("country")}
        if not all(c in fams for c in COUNTRIES):
            continue
        shared = fams[FRANCE] & fams[BRAZIL]
        if shared:
            # most cross-comparable shared family, by METRIC_FAMILIES order
            fam = min(shared, key=lambda f: METRIC_FAMILIES.index(f)
                      if f in METRIC_FAMILIES else 99)
            sub = grp[grp["metric_family"] == fam]
            cross[sector] = False
        else:
            sub = grp
            cross[sector] = True
        keep.append(sub)

    if not keep:
        return sel.head(0)
    sel = pd.concat(keep)
    sel = (sel.sort_values("target_year")
              .drop_duplicates(["country", "sector"], keep="last"))

    wide = sel.pivot_table(
        index="sector", columns="country",
        values=["target_value", "target_year", "latest_value"],
        aggfunc="first",
    )
    wide.columns = [f"{a}__{b}" for a, b in wide.columns]

    meta = sel.set_index(["sector", "country"])[["metric_family", "basis", "comparable"]]
    for field in ("metric_family", "basis", "comparable"):
        col = meta[field].unstack()
        for country in COUNTRIES:
            if country in col.columns:
                wide[f"{field}__{country}"] = col[country]

    wide = wide.reset_index()
    need = [f"target_value__{c}" for c in COUNTRIES]
    if any(c not in wide.columns for c in need):
        return wide.head(0)
    both = wide.dropna(subset=need).copy()
    if both.empty:
        return both

    def _same(r) -> bool:
        try:
            return (bool(r[f"comparable__{FRANCE}"])
                    and bool(r[f"comparable__{BRAZIL}"])
                    and r[f"basis__{FRANCE}"] == r[f"basis__{BRAZIL}"])
        except KeyError:
            return False

    both["same_basis"] = both.apply(_same, axis=1)
    both["cross_family"] = both["sector"].map(cross).fillna(True)
    return both


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    """Which sectors carry a target in each country -- the structural asymmetry."""
    sel = df[df["level"] == SECTOR]
    return (sel.groupby(["sector", "country"]).size()
               .unstack(fill_value=0).reindex(columns=COUNTRIES, fill_value=0))
