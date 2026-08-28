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

import io
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------
# where the data comes from
#
# Two sources, checked in this order:
#
#   1. data/raw/<file>          -- local working copy, used for development
#   2. st.secrets["data"][...]  -- a URL, used by the deployed app
#
# The extracts are deliberately NOT committed to the repository, so a fresh
# clone (which is what Streamlit Community Cloud builds from) has no data
# directory at all and falls through to the secrets URL.
#
# SECURITY: those URLs are credentials. A pre-signed S3/GCS link or a share
# link with an embedded token grants whoever holds it read access to the file.
# So they live in `.streamlit/secrets.toml` (gitignored) locally and in the
# Streamlit Cloud "Secrets" settings pane in the deployment -- never in git,
# never in a log line, and never in an error message. `_scrub` below exists to
# keep them out of exception text, which is the easy way to leak one.
#
# Expected secrets shape:
#
#   [data]
#   msm_url = "https://..."   # REP.csv
#   trt_url = "https://..."   # traitements_REP.csv
#   ref_url = "https://..."   # Referentiels_MSM.xlsx
# --------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"

DOWNLOAD_TIMEOUT = 60


@dataclass(frozen=True)
class Source:
    key: str        # cache key and the name used in messages
    filename: str   # expected name under data/raw
    secret: str     # key inside the [data] secrets table
    label: str      # human description


SOURCES = (
    Source("msm", "REP.csv", "msm_url", "put-on-market declarations"),
    Source("trt", "traitements_REP.csv", "trt_url", "treated-waste declarations"),
    Source("ref", "Referentiels_MSM.xlsx", "ref_url", "actor and filiere referentials"),
)
BY_KEY = {s.key: s for s in SOURCES}

_URL_RE = re.compile(r"https?://\S+")


def _scrub(text: str) -> str:
    """Strip any URL out of a message before it is shown or logged."""
    return _URL_RE.sub("<url hidden>", str(text))


def _local(src: Source) -> Path:
    return RAW / src.filename


def _secret_url(src: Source) -> str | None:
    """The configured URL for this source, or None.

    st.secrets raises rather than returning empty when no secrets exist at all,
    so every access is guarded.
    """
    try:
        value = st.secrets["data"][src.secret]
    except Exception:
        return None
    value = str(value).strip()
    return value or None


@st.cache_data(show_spinner="Fetching data…")
def _fetch(key: str) -> bytes:
    """Download one source. Cached on the KEY, never on the URL.

    Caching on the key rather than the URL keeps the credential out of the
    cache index, and means rotating the URL does not silently orphan a cache
    entry keyed to the old one.
    """
    src = BY_KEY[key]
    url = _secret_url(src)
    if not url:
        raise RuntimeError(f"No URL configured for '{src.key}'.")
    request = urllib.request.Request(
        url, headers={"User-Agent": "circular-econ-dashboard"})
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"'{src.key}' returned HTTP {exc.code}. If the link is pre-signed it "
            "may have expired; if it is a share link, check it is set to "
            "anyone-with-the-link."
        ) from None
    except Exception as exc:
        raise RuntimeError(f"'{src.key}' could not be fetched: "
                           f"{_scrub(exc)}") from None


def _open(key: str):
    """A path or an in-memory buffer for this source, whichever is available.

    pandas accepts either, so callers do not need to care which one they got.
    """
    src = BY_KEY[key]
    local = _local(src)
    if local.exists():
        return local
    if _secret_url(src):
        return io.BytesIO(_fetch(key))
    return None


def resolve_optional(filename: str, secret_key: str):
    """Path or buffer for an OPTIONAL file, or None if it is not available.

    Same local-then-secrets order as the required sources, but absence is a
    normal state rather than an error -- the targets file is optional because
    the page falls back to its placeholder set when it is missing.
    """
    local = RAW / filename
    if local.exists():
        return local
    try:
        url = str(st.secrets["data"][secret_key]).strip()
    except Exception:
        return None
    if not url:
        return None
    request = urllib.request.Request(
        url, headers={"User-Agent": "circular-econ-dashboard"})
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
            return io.BytesIO(response.read())
    except Exception as exc:
        raise RuntimeError(
            f"'{secret_key}' could not be fetched: {_scrub(exc)}") from None


def data_origin() -> str:
    """Where the data is being read from, for display in the UI."""
    local = sum(1 for s in SOURCES if _local(s).exists())
    if local == len(SOURCES):
        return "local files"
    if local == 0:
        return "remote storage"
    return "a mix of local files and remote storage"


def require_data() -> None:
    """Check configuration, then prime the loaders, before any chart runs.

    Two jobs, both about failing legibly. Streamlit Community Cloud redacts
    exception text to avoid leaking data, so an unguarded pandas error reaches
    the user as "The original error message is redacted" with no clue which
    file is missing. This surfaces the real problem instead.

    It also PRIMES the loaders rather than only checking paths: a download that
    401s or times out would otherwise surface deep inside a chart, redacted.
    Doing it here funnels every failure mode through one readable place.

    Deliberately NOT decorated with @st.cache_data: st.stop() raises a control
    -flow exception, and caching a function that raises it would poison the
    cache entry.
    """
    unconfigured = [
        s for s in SOURCES if not _local(s).exists() and not _secret_url(s)
    ]
    if unconfigured:
        rows = "\n".join(
            f"- **{s.label}** — expected at `data/raw/{s.filename}`, "
            f"or a URL in secrets under `data.{s.secret}`"
            for s in unconfigured
        )
        st.error(
            "**No data source is configured.**\n\n"
            f"{rows}\n\n"
            "The extracts are deliberately not committed to the repository, so "
            "the deployed app reads them from private storage instead. Add a "
            "`[data]` section to the app's secrets:\n\n"
            "```toml\n[data]\n"
            'msm_url = "https://…/REP.csv"\n'
            'trt_url = "https://…/traitements_REP.csv"\n'
            'ref_url = "https://…/Referentiels_MSM.xlsx"\n'
            "```\n\n"
            "On Streamlit Community Cloud: **Manage app → Settings → Secrets**. "
            "Locally: create `.streamlit/secrets.toml` (already gitignored). "
            "Pre-signed S3/GCS links, or Drive/Dropbox direct-download links, "
            "all work — anything the server can GET without a login."
        )
        st.stop()

    try:
        load_msm()
        load_treatment()
        load_actors()
    except Exception as exc:
        st.error(
            "**The data could not be loaded.**\n\n"
            f"{_scrub(exc)}\n\n"
            "The URLs are configured, so this is a fetch or parse problem "
            "rather than a missing setting. Check the link has not expired and "
            "still points at the right file."
        )
        st.stop()


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
    df = pd.read_csv(_open("msm"), low_memory=False)
    df["filiere_en"] = df["filiere"].map(FILIERE_EN).fillna(df["filiere"])
    return df


@st.cache_data(show_spinner=False)
def load_treatment() -> pd.DataFrame:
    """Treated-waste declarations. Semicolon-separated, unlike REP.csv."""
    df = pd.read_csv(_open("trt"), sep=";", low_memory=False)

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
    return pd.read_excel(_open("ref"), sheet_name="Acteurs")


@st.cache_data(show_spinner=False)
def load_filieres() -> pd.DataFrame:
    return pd.read_excel(_open("ref"), sheet_name="Filieres")


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
