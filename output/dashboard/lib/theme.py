"""
AUTHOR: Arthur Briens
DATE: 19/08/2026

Palette, Plotly templates and page chrome for the circularity dashboard.

The categorical order below is validated for colour-vision deficiency in both
light and dark mode (worst adjacent pair dE 9.1 light / 8.4 dark on the OKLab
x100 scale, against a >= 8 gate). Do not re-order or insert hues without
re-validating -- the ORDER is the safety mechanism, not decoration.

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

import plotly.graph_objects as go
import plotly.io as pio

# --------------------------------------------------------------------------
# palette
# --------------------------------------------------------------------------

LIGHT = {
    "surface": "#fcfcfb",
    "plane": "#f9f9f7",
    "text_primary": "#0b0b0b",
    "text_secondary": "#52514e",
    "text_muted": "#898781",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    "track": "#ebeae4",
    # categorical, fixed order
    "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
               "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    # ordinal ramp (waste hierarchy): never lighter than step 250 on light
    "ordinal": ["#1c5cab", "#2a78d6", "#5598e7", "#86b6ef"],
    # sequential ramp (magnitude): full range allowed
    "sequential": ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5",
                   "#256abf", "#184f95", "#0d366b"],
}

DARK = {
    "surface": "#1a1a19",
    "plane": "#0d0d0d",
    "text_primary": "#ffffff",
    "text_secondary": "#c3c2b7",
    "text_muted": "#898781",
    "grid": "#2c2c2a",
    "axis": "#383835",
    "track": "#2c2c2a",
    "series": ["#3987e5", "#d95926", "#199e70", "#c98500",
               "#d55181", "#008300", "#9085e9", "#e66767"],
    "ordinal": ["#cde2fb", "#9ec5f4", "#5598e7", "#184f95"],
    "sequential": ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5",
                   "#256abf", "#184f95", "#0d366b"],
}

# status colours are reserved -- never reused as a series colour
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def palette(dark: bool = False) -> dict:
    """Return the active palette dict."""
    return DARK if dark else LIGHT


# --------------------------------------------------------------------------
# plotly template
# --------------------------------------------------------------------------

def _template(p: dict) -> go.layout.Template:
    axis = dict(
        showgrid=True,
        gridcolor=p["grid"],
        gridwidth=1,
        zeroline=False,
        linecolor=p["axis"],
        linewidth=1,
        ticks="",
        tickfont=dict(color=p["text_muted"], size=11),
        title=dict(font=dict(color=p["text_secondary"], size=12)),
        automargin=True,
    )
    return go.layout.Template(
        layout=go.Layout(
            font=dict(family=FONT, size=12, color=p["text_secondary"]),
            # explicit, not transparent: the palette's CVD and contrast checks
            # were run against THIS surface, so letting the chart inherit
            # whatever is behind it would invalidate them -- and in dark mode it
            # left the plot area white under a dark page
            paper_bgcolor=p["surface"],
            plot_bgcolor=p["surface"],
            colorway=p["series"],
            xaxis=axis,
            yaxis=axis,
            margin=dict(l=8, r=8, t=8, b=8),
            hoverlabel=dict(
                bgcolor=p["surface"],
                bordercolor=p["axis"],
                font=dict(family=FONT, size=12, color=p["text_primary"]),
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="left", x=0,
                font=dict(color=p["text_secondary"], size=12),
                title=dict(text=""),
            ),
            title=dict(font=dict(color=p["text_primary"], size=14)),
            bargap=0.35,
        )
    )


def register_templates() -> None:
    """Register 'circ_light' / 'circ_dark' with Plotly."""
    pio.templates["circ_light"] = _template(LIGHT)
    pio.templates["circ_dark"] = _template(DARK)


def template_name(dark: bool = False) -> str:
    return "circ_dark" if dark else "circ_light"


# --------------------------------------------------------------------------
# page chrome
# --------------------------------------------------------------------------

def page_css(dark: bool = False) -> str:
    """CSS injected once per page: hero metric + surface colours."""
    p = palette(dark)
    return f"""
    <style>
      .stApp {{ background: {p['plane']}; }}
      [data-testid="stHeader"] {{ background: transparent; }}
      [data-testid="stSidebarContent"] {{ background: {p['surface']}; }}

      /* Streamlit paints its own type from config.toml, which is STATIC and so
         cannot follow this toggle. Without these rules the page title and every
         caption stay near-black on a dark plane and vanish. */
      .stApp h1, .stApp h2, .stApp h3, .stApp h4,
      .stApp p, .stApp li, .stApp label, .stApp strong {{
          color: {p['text_primary']};
      }}
      [data-testid="stCaptionContainer"],
      [data-testid="stCaptionContainer"] p {{ color: {p['text_muted']}; }}

      /* charts get the same card treatment as the metric tiles, so the plot
         surface and the tile surface are visibly one system */
      [data-testid="stPlotlyChart"] {{
          background: {p['surface']};
          border: 1px solid {p['grid']};
          border-radius: 10px;
          overflow: hidden;
      }}
      div[data-testid="stMetric"] {{
          background: {p['surface']};
          border: 1px solid {p['grid']};
          border-radius: 10px;
          padding: 14px 18px 12px;
      }}
      div[data-testid="stMetricValue"] {{
          font-size: 30px; font-weight: 600; color: {p['text_primary']};
          font-variant-numeric: normal;
      }}
      div[data-testid="stMetricLabel"] p {{
          font-size: 12.5px; color: {p['text_secondary']};
      }}
      /* the hero: exactly one per view -- the first metric column on the page.
         Streamlit renders a markdown wrapper as a SIBLING of the metric, not a
         parent, so a wrapping <div class="hero"> cannot reach it. */
      div[data-testid="stHorizontalBlock"]:first-of-type
        div[data-testid="stColumn"]:first-child
        div[data-testid="stMetricValue"] {{ font-size: 50px; }}
      .caveat {{
          border: 1px solid {p['grid']};
          border-left: 3px solid {STATUS['warning']};
          border-radius: 8px;
          padding: 10px 14px;
          background: {p['surface']};
          color: {p['text_secondary']};
          font-size: 13px;
          margin-bottom: 8px;
      }}
      .sect {{
          font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
          color: {p['text_muted']}; font-weight: 600;
          margin: 26px 0 2px;
      }}
    </style>
    """
