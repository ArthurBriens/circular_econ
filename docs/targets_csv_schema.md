# `targets_fr_br.csv` — file specification

The France/Brazil targets comparison page reads this file. It is **optional**:
when absent, the page falls back to the invented placeholder set in
`output/dashboard/lib/targets.py` and shows a banner saying so.

## Where to put it

Resolved in this order:

1. `data/raw/targets_fr_br.csv` — the working copy
2. `st.secrets["data"]["targets_url"]` — a URL, as a fallback

**Unlike the ADEME extracts, this file IS committed to git.** The line the
repository draws is *third-party bulk extracts out, our own research in*: the
three ADEME files total ~4.5 MB, are redownloadable at any time, and are served
to the deployed app from `st.secrets`; this one is 84 KB of hand-assembled,
individually sourced rows, and committing it is what makes the targets page
reproducible from a clone.

The `targets_url` secret still works and still takes second place, so you can
override the committed file with a newer copy in storage without a code change.

## Format

Plain CSV, **comma-separated**, UTF-8, one header row, **19 columns in any
order**. Save from Excel as "CSV UTF-8 (Comma delimited)" — not semicolon.

> A French/Portuguese locale Excel defaults to semicolons and comma decimals.
> Both break the read. Check the file in a text editor before uploading.

## Columns

The placeholder set are a working example — press
**Download CSV template** on the page to get a correctly-headed file.

### `status` — three values, not two

- **`placeholder`** — invented, present only so the layout renders.
- **`sourced`** — from a real instrument and cited in `source_url`, but not read
  in the primary legal text (a secondary source, or a transcription of an annex).
- **`verified`** — read in the instrument's own text, or on the regulator's
  official page.

Only `verified` counts towards the meter at the top of the page. The middle
value exists because "placeholder" would misdescribe a row that is real but
second-hand, and "verified" would overclaim it.

| # | Column | Required | Allowed values | Notes |
|---|--------|----------|----------------|-------|
| 1 | `country` | **yes** | `France` or `Brazil` exactly | Any other value **rejects the whole file** |
| 2 | `level` | **yes** | `government` or `sector`, lowercase | Chooses the page section. Any other value **rejects the whole file** |
| 3 | `tier` | free text | e.g. `EU`, `National`, `Regional`, `Federal`, `State`, `Sector agreement` | Shown in the government table |
| 4 | `sector` | free text | e.g. `All municipal waste`, `Packaging`, `EEE`, `Tyres` | **The pairing key.** Must match *exactly* between the two countries for a sector to appear in the paired chart |
| 5 | `metric_family` | free text | one of the six below | Sidebar filter. A value outside the list is filtered out and effectively invisible |
| 6 | `metric` | free text | the metric as the instrument words it | Row label |
| 7 | `basis` | free text | the denominator, in plain words | **Load-bearing** — see below |
| 8 | `unit` | **yes for charts** | `%`, `Mt`, `kg/cap`, `count` | Only rows with `%` appear in the bar and progress charts. Others reach the tables only |
| 9 | `baseline_value` | number | | Blank is fine |
| 10 | `baseline_year` | year | e.g. `2015` | Needed for the horizon chart |
| 11 | `latest_value` | number | | Needed for the progress chart |
| 12 | `latest_year` | year | | |
| 13 | `target_value` | number | | Needed for nearly every chart |
| 14 | `target_year` | year | | Needed for the horizon chart |
| 15 | `instrument` | free text | e.g. `Planares Decreto 11.043/2022` | Cite the instrument, not a summary |
| 16 | `comparable` | boolean | `TRUE` / `FALSE` | See below |
| 17 | `status` | **yes** | `placeholder`, `sourced` or `verified` | See below. Only `verified` counts towards the meter |
| 18 | `note` | free text | | Blank is fine |
| 19 | `source_url` | free text | a URL | Where the figure came from. Blank is allowed but discouraged |

### `metric_family` — the six values

```
Recycling rate
Separate collection rate
Landfill diversion
Collection coverage
Reuse & preparation for reuse
Reverse-logistics recovery
```

Edit the list in `lib/targets.METRIC_FAMILIES` if you need another. This
grouping is *our editorial judgement*, not a legal category — it is the most
contestable field in the file and is meant to be argued with.

`Landfill diversion` is also listed in `LOWER_IS_BETTER`, so those rows get a
down-arrow and a short bar is not read as poor performance. Add any other
family where falling is good to that set.

### `basis` and `comparable` — the two that matter most

These decide whether France and Brazil are allowed to share an axis.

- **`basis`** is the denominator in plain words: *"Packaging placed on market"*
  versus *"Packaging placed on market by signatory firms"*. Write it out even
  when it feels obvious.
- **`comparable`** is your judgement that this row's footing matches the other
  country's for the same family.

A pair is drawn on a shared axis **only when both sides are `TRUE` and the two
`basis` strings are identical**. Anything else gets a `≠` prefix and the
mismatch is stated. So a typo in `basis` will correctly-but-annoyingly mark a
genuine pair as mismatched — copy the string between the two rows when they
really do share a denominator.

Accepted booleans, case-insensitive: `TRUE/FALSE`, `yes/no`, `1/0`,
`oui/non`, `sim/não`. **Anything unrecognised, or blank, is treated as
`FALSE`** — the safe direction, since the cost of wrongly claiming
comparability is a misleading chart.

## What causes the file to be rejected

The loader rejects the **whole file** (falling back to placeholders, with the
reason shown in red on the page) if:

- any of the 19 columns is missing, or a header is misspelled
- `country` contains anything other than `France` / `Brazil`
- `level` contains anything other than `government` / `sector`

It does **not** reject, but silently coerces:

- a non-numeric value in any of the six numeric columns becomes blank — so
  `n/a`, `~50`, `50%` or `1 234` in `target_value` all quietly become empty.
  Write bare numbers: `50`, not `50%`; `1234`, not `1 234`.

## Two worked rows

A government target where the two countries genuinely share a basis:

```csv
country,level,tier,sector,metric_family,metric,basis,unit,baseline_value,baseline_year,latest_value,latest_year,target_value,target_year,instrument,comparable,status,note
France,government,EU,All municipal waste,Recycling rate,Preparation for reuse and recycling of municipal waste,Total municipal waste generated,%,42,2015,49,2023,55,2025,EU Waste Framework Directive,TRUE,verified,Checked against the directive text
```

A sector target where they do not:

```csv
Brazil,sector,Sector agreement,Packaging,Reverse-logistics recovery,Packaging recovered through reverse logistics,Packaging placed on market by signatory firms,%,22,2018,30,2024,50,2031,Acordo Setorial de Embalagens,FALSE,placeholder,Signatory-firm basis - narrower than the French REP basis
```

## Working practice

Fill `status` as `placeholder` while drafting and flip to `verified` once you
have checked that row against the instrument itself. The meter at the top of
the page tracks how far that has got, so the page is honest about its own
provenance while you work through it.

Multiple rows per country per sector are fine and expected — a staged target
series (55 % by 2025, 65 % by 2035) is simply two rows. The paired chart takes
the furthest-horizon target per country per sector.
