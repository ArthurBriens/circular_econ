"""
AUTHOR: Arthur Briens
DATE: 19/08/2026

Loading and reshaping of the ADEME / SYDEREP extracts in data/raw.

Granularity note (per CLAUDE.md): the declarations are national by eco-organism
for put-on-market, and TREATMENT-SITE regional for the treatment file. Neither
is municipal. `dep_site_trt` is the finest available level and refers to where
the waste was TREATED, not where it was collected -- so it must not be read as
a municipal or even a regional collection performance measure.

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

# --------------------------------------------------------------------------
# paths -- resolved from this file, so the app runs from any working directory
# --------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"

MSM_CSV = RAW / "REP.csv"
TRT_CSV = RAW / "traitements_REP.csv"
REF_XLSX = RAW / "Referentiels_MSM.xlsx"


# --------------------------------------------------------------------------
# labels
# --------------------------------------------------------------------------

FILIERE_EN = {
    "ABJ": "DIY & garden equipment",
    "ASL": "Sports & leisure goods",
    "BAT": "Batteries",
    "BPS": "Pleasure boats",
    "DISP_MED": "Sharps medical devices",
    "EA": "Furniture",
    "EEE": "Electrical & electronic equipment",
    "EMPAP": "Household packaging & graphic paper",
    "EPRO": "Industrial packaging",
    "JOUET": "Toys",
    "LUB": "Lubricant oils",
    "MNU": "Unused medicines",
    "PAP": "Graphic paper",
    "PCHIM": "Chemical products",
    "PMCB": "Construction products & materials",
    "PNEU": "Tyres",
    "TABAC": "Tobacco products",
    "TLC": "Textiles, household linen & footwear",
    "VEHICULE": "End-of-life vehicles",
}

# The four flagship filieres agreed for v1.
FLAGSHIP = ["EMPAP", "EEE", "TLC", "EA"]

# PLACEHOLDER -- regulatory collection targets are not in the downloaded
# extracts. These are stand-ins so the chart shape is reviewable; replace them
# with the published values from the ADEME filiere fact sheets before use.
PLACEHOLDER_TARGETS = {"EMPAP": 75.0, "EEE": 65.0, "TLC": 60.0, "EA": 65.0}

# --------------------------------------------------------------------------
# treatment-code -> waste-hierarchy bucket
#
# Ordered prefix rules. Anything unmatched lands in "Unclassified" and is shown
# as such rather than silently folded into a bucket -- ADEME's typ_trt list has
# 73 codes including legacy variants, and a wrong mapping here would quietly
# corrupt every composition chart.
# --------------------------------------------------------------------------

HIERARCHY = ["Reuse", "Recycling", "Other recovery", "Disposal", "Unclassified"]

_RULES: list[tuple[str, str]] = [
    ("PRE_ELIM", "Disposal"),
    ("ELIM", "Disposal"),
    ("PREPA_REUTILISATION", "Reuse"),
    ("EN_VUE_REMPLOI", "Reuse"),
    ("EN_VUE_REUT", "Reuse"),
    ("REEMP", "Reuse"),
    ("REEM", "Reuse"),
    ("OCCAS", "Reuse"),
    ("PIEC", "Reuse"),
    ("RECH", "Reuse"),
    ("RR", "Reuse"),
    ("RECY", "Recycling"),
    ("REC_", "Recycling"),
    ("REGE", "Recycling"),
    ("GRANU", "Recycling"),
    ("AUTRE_VALO_MAT", "Recycling"),
    ("BROYAGE", "Recycling"),
    ("VALO", "Other recovery"),
    ("AUTREVAL", "Other recovery"),
    ("CHAU", "Other recovery"),
    ("INCIN", "Other recovery"),
]


def bucket_of(code: str) -> str:
    if not isinstance(code, str):
        return "Unclassified"
    for prefix, bucket in _RULES:
        if code.startswith(prefix):
            return bucket
    return "Unclassified"


# --------------------------------------------------------------------------
# region crosswalk
#
# reg_site_trt carries PRE-2016 region codes (22 metropolitan regions + DOM),
# not the current 13. Mapping is one-way and lossless in this direction.
# --------------------------------------------------------------------------

LEGACY_REGION = {
    11: "Ile-de-France",
    21: "Grand Est", 41: "Grand Est", 42: "Grand Est",
    22: "Hauts-de-France", 31: "Hauts-de-France",
    23: "Normandy", 25: "Normandy",
    24: "Centre-Val de Loire",
    26: "Bourgogne-Franche-Comte", 43: "Bourgogne-Franche-Comte",
    52: "Pays de la Loire",
    53: "Brittany",
    54: "Nouvelle-Aquitaine", 72: "Nouvelle-Aquitaine", 74: "Nouvelle-Aquitaine",
    73: "Occitanie", 91: "Occitanie",
    82: "Auvergne-Rhone-Alpes", 83: "Auvergne-Rhone-Alpes",
    93: "Provence-Alpes-Cote d'Azur",
    94: "Corsica",
    1: "Guadeloupe", 2: "Martinique", 3: "French Guiana",
    4: "Reunion", 6: "Mayotte",
}

# schematic tile grid (col, row) -- equal area per region, so the colour is not
# biased by territory size the way a true choropleth would be
REGION_TILES = {
    "Hauts-de-France": (2, 0),
    "Normandy": (1, 1), "Ile-de-France": (2, 1), "Grand Est": (3, 1),
    "Brittany": (0, 2), "Pays de la Loire": (1, 2),
    "Centre-Val de Loire": (2, 2), "Bourgogne-Franche-Comte": (3, 2),
    "Nouvelle-Aquitaine": (1, 3), "Auvergne-Rhone-Alpes": (2, 3),
    "Occitanie": (1, 4), "Provence-Alpes-Cote d'Azur": (2, 4), "Corsica": (3, 4),
}
DOM_TILES = {
    "Guadeloupe": (0, 0), "Martinique": (1, 0), "French Guiana": (2, 0),
    "Reunion": (3, 0), "Mayotte": (4, 0),
}

# explicit short codes -- deriving initials gives "N" for Normandy and "C" for
# Corsica, which are unreadable on a tile
REGION_SHORT = {
    "Hauts-de-France": "HDF", "Normandy": "NOR", "Ile-de-France": "IDF",
    "Grand Est": "GES", "Brittany": "BRE", "Pays de la Loire": "PDL",
    "Centre-Val de Loire": "CVL", "Bourgogne-Franche-Comte": "BFC",
    "Nouvelle-Aquitaine": "NAQ", "Auvergne-Rhone-Alpes": "ARA",
    "Occitanie": "OCC", "Provence-Alpes-Cote d'Azur": "PAC", "Corsica": "COR",
    "Guadeloupe": "GLP", "Martinique": "MTQ", "French Guiana": "GUF",
    "Reunion": "REU", "Mayotte": "MYT",
}


# --------------------------------------------------------------------------
# loaders
# --------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_msm() -> pd.DataFrame:
    """Put-on-market declarations (REP.csv). One row per declaring actor."""
    df = pd.read_csv(MSM_CSV, low_memory=False)
    df["filiere_en"] = df["filiere"].map(FILIERE_EN).fillna(df["filiere"])
    return df


@st.cache_data(show_spinner=False)
def load_treatment() -> pd.DataFrame:
    """Treated-waste declarations. Semicolon-separated, unlike REP.csv."""
    df = pd.read_csv(TRT_CSV, sep=";", low_memory=False)

    # typ_trt is absent for whole filieres (EMPAP declares supported tonnage,
    # not treatment operations). Keep that distinguishable from "code we failed
    # to map" -- otherwise a filiere with no breakdown at all renders as 100 %
    # Unclassified and looks like a mapping failure.
    df["has_code"] = df["typ_trt"].notna()
    df["bucket"] = df["typ_trt"].map(bucket_of)

    # type_ton is null for most filieres; fill before it is ever used as a
    # grouping key, or those rows get silently dropped by groupby/merge.
    df["type_ton"] = df["type_ton"].fillna("N/A")

    df["region"] = (
        pd.to_numeric(df["reg_site_trt"], errors="coerce")
        .astype("Int64")
        .map(LEGACY_REGION)
    )

    # three states, not two: a null country is unknown, not "abroad"
    df["location"] = df["pays_site_trt"].map(
        lambda c: "Treated in France" if c == "FR"
        else ("Country not declared" if pd.isna(c) else "Treated abroad")
    )
    df["filiere_en"] = df["filiere"].map(FILIERE_EN).fillna(df["filiere"])
    return df


@st.cache_data(show_spinner=False)
def load_actors() -> pd.DataFrame:
    """Actor id -> company name."""
    return pd.read_excel(REF_XLSX, sheet_name="Acteurs")


@st.cache_data(show_spinner=False)
def load_filieres() -> pd.DataFrame:
    return pd.read_excel(REF_XLSX, sheet_name="Filieres")


# --------------------------------------------------------------------------
# transforms
# --------------------------------------------------------------------------

def msm_by_year(df: pd.DataFrame, filieres: list[str]) -> pd.DataFrame:
    """Total tonnage put on market, by year and filiere."""
    out = df[df["filiere"].isin(filieres)]
    return out.groupby(["annee", "filiere", "filiere_en"], as_index=False)["tonnage"].sum()


def msm_by_actor(df: pd.DataFrame, actors: pd.DataFrame, filiere: str) -> pd.DataFrame:
    """Tonnage put on market by eco-organism / individual system, per year."""
    out = (
        df[df["filiere"] == filiere]
        .groupby(["annee", "acteur"], as_index=False)["tonnage"].sum()
        .merge(actors, left_on="acteur", right_on="Acteur", how="left")
    )
    out["name"] = out["raison_sociale"].fillna(out["acteur"]).str.title()
    total = out.groupby("annee")["tonnage"].transform("sum")
    out["share"] = out["tonnage"] / total * 100
    return out


def treatment_mix(
    df: pd.DataFrame, filieres: list[str], year: int
) -> tuple[pd.DataFrame, list[str]]:
    """Share of each hierarchy bucket, per filiere, for one year.

    Returns (mix, skipped) where `skipped` lists filieres that declare no
    treatment code at all for that year -- they are excluded rather than drawn
    as a 100 % Unclassified bar, which would misread as a mapping failure.

    Sums are taken WITHIN a single type_ton per filiere: the tonnage-type codes
    (OPE / TON_SOU / FIN ...) are alternative accounting bases and adding them
    together double-counts. The dominant code per filiere is used.
    """
    sel = df[(df["filiere"].isin(filieres)) & (df["annee"] == year)]
    if sel.empty:
        return sel.assign(share=pd.Series(dtype=float)), []

    coded = sel[sel["has_code"]]
    skipped = sorted(set(sel["filiere"]) - set(coded["filiere"]))
    if coded.empty:
        return coded.assign(share=pd.Series(dtype=float)), skipped

    dominant = (
        coded.groupby(["filiere", "type_ton"])["masse"].sum()
        .reset_index().sort_values("masse", ascending=False)
        .drop_duplicates("filiere")[["filiere", "type_ton"]]
    )
    coded = coded.merge(dominant, on=["filiere", "type_ton"], how="inner")
    grp = coded.groupby(["filiere", "filiere_en", "bucket"], as_index=False)["masse"].sum()
    total = grp.groupby("filiere")["masse"].transform("sum")
    grp["share"] = grp["masse"] / total * 100
    return grp, skipped


def treatment_by_region(df: pd.DataFrame, filieres: list[str], year: int) -> pd.DataFrame:
    out = df[(df["filiere"].isin(filieres)) & (df["annee"] == year) & df["region"].notna()]
    return out.groupby("region", as_index=False)["masse"].sum()


LOCATIONS = ["Treated in France", "Treated abroad", "Country not declared"]


def domestic_split(df: pd.DataFrame, filieres: list[str], year: int) -> pd.DataFrame:
    """Treated in France vs abroad vs not declared -- export exposure.

    NB: the column is `location`, never `where` -- `df.where` is a DataFrame
    method, so attribute access would silently return the method instead of data.
    """
    out = df[(df["filiere"].isin(filieres)) & (df["annee"] == year)]
    grp = out.groupby(["filiere", "filiere_en", "location"], as_index=False)["masse"].sum()
    total = grp.groupby("filiere")["masse"].transform("sum")
    grp["share"] = grp["masse"] / total * 100
    return grp


def coverage_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Which filiere x year cells actually carry treatment data."""
    return (
        df.pivot_table(index="filiere", columns="annee", values="masse", aggfunc="sum")
        .notna()
    )
