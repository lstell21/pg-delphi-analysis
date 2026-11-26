# Pandemic guidelines: Delphi analysis and review synthesis

Analysis code for "Preparing for the Next Pandemic Takes More Than Better Models:
Expert Consensus Recommendations for Infectious Disease Modelling."

Everything the paper reports as a number is produced here. The pipeline reads the
Round 4 survey export and the literature screening results, and writes the
consensus statistics, the theme coverage, and every table and figure.

## What lives where

| Component | Contents | Location |
| --- | --- | --- |
| **This repository** | Delphi analysis, theme codebook, table and figure builders | [10.5281/zenodo.22233244](https://doi.org/10.5281/zenodo.22233244) |
| **Screening instrument** | LLM full-text screening against the five inclusion criteria | [10.5281/zenodo.22647106](https://doi.org/10.5281/zenodo.22647106) |
| **Data deposit** | Round 4 survey data, screening export, hand labels, statement provenance, recoding sheets, discipline and PRISMA counts | [10.5281/zenodo.22232255](https://doi.org/10.5281/zenodo.22232255) |

## Getting the data

The data is not in this repository. Download the deposit and unpack it into
`data/` at this root. Its structure is already the one the code expects, so there
is nothing to rearrange.

```
data/
  delphi/                             from the deposit
    round4_raw_export.csv               unmodified LimeSurvey export
    round4_merged_record.csv            the one reconstructed response
    round4_codebook.md                  what each variable is
    round3_statement_analyses.json      read by the round comparison
    round4_panel_characteristics.csv    demographic counts over the 41 completers
    provenance/                         drafts, mappings and Round 1 transcription
    mustact/                            the six blind recoding sheets, as CSV
    contributors/                       discipline counts only
  literature/                         from the deposit
    articles-full-screen-results.csv    159 screened publications
    theme_labels_tuning.csv             tuning sample, 30 publications
    theme_labels_holdout.csv            held-out sample, 30
    theme_labels_holdout_clean.csv      held out, 5 overlaps removed, 25
    prisma_counts.csv                   the counts behind the PRISMA flow diagram
  generated/                          written by the pipeline
```

The pipeline never writes into the two deposit folders, so your copy stays
pristine and `rm -rf data/generated` is a complete clean. It produces
`round4_dataset.csv`, `round4_responses.json`, `consensus_stats.json` and `.csv`,
`round3_vs_round4.json`, `rankings.json`, `sensitivity.json`, the provenance chain,
the recoding agreement, and the theme assignments. `scripts/config.py`
resolves every path from the repository root, so nothing needs configuring.

## Quick start

```bash
python -m venv venv
venv\Scripts\activate        # Windows; source venv/bin/activate elsewhere
pip install -r requirements.txt

python scripts/r4_build_dataset.py           # raw export -> round4_dataset.csv
python scripts/run_round4_pipeline.py
python scripts/lit_theme_synthesis.py --run data/literature/articles-full-screen-results.csv
python scripts/lit_theme_synthesis.py --run data/literature/articles-full-screen-results.csv --by-period
python scripts/lit_review_tables.py --run data/literature/articles-full-screen-results.csv
python scripts/main_text_tables.py
python scripts/priorities_table.py
python scripts/statement_provenance.py
python scripts/statement_origin_agreement.py
python scripts/mustact_recode.py score
python scripts/contributor_table.py --from-counts
python scripts/generate_prisma_flow.py
python scripts/generate_delphi_flowchart.py
python scripts/generate_round_flow_chart.py
```

Tables land in `tables/`, figures in `figures/`, and the two Supplementary Data
files in `supplementary_data/`. `\input` the tables from wherever
the manuscript sources live. Developed on Python 3.14, and `requirements.txt`
pins the versions the paper's results used. The only dependencies are `numpy`
and `matplotlib`. Nothing here reaches a network or needs an API key.

These are the scripts that produced the paper's numbers, with the data and
output paths rewritten for release. No statistic, threshold, or table layout
changed.

## Pipeline

`r4_build_dataset.py` runs once. It assembles the analysis dataset from the raw
LimeSurvey export plus a single reconstructed record, dropping superseded rows and
abandoned reattempts and printing every removed response identifier with its
reason. The Supplementary Information's note on response handling describes the
reconstruction.
`run_round4_pipeline.py` then runs the stages in order:

| Stage | Script | Writes |
| --- | --- | --- |
| 1 | `r4_extract_from_csv.py` | `round4_responses.json` |
| 2 | `r4_consensus_stats.py` | `consensus_stats.json`, `consensus_stats.csv` |
| 3 | `r4_round_comparison.py` | `round3_vs_round4.json` |
| 4 | `r4_rankings.py` | Section E ranking aggregates |
| 5 | `r4_sensitivity.py` | `sensitivity.json`, `sensitivity.csv`, completers-only table |
| 6 | `r4_latex_tables.py` | consensus and panel tables, rankings table, round comparison and rankings figures, Supplementary Data 2 |

Every stage is deterministic and reproduces the reported statistics.

`lit_theme_synthesis.py` holds the theme codebook. The eight themes and their term
lists live in the `THEMES` constant, and the script renders them into
`theme_codebook.tex` so the table in the paper and the executed code cannot drift
apart. It also scores the codebook against the hand labels:

```bash
python scripts/lit_theme_synthesis.py --run data/literature/articles-full-screen-results.csv \
    --validate data/literature/theme_labels_holdout.csv
```

That reproduces precision 0.82, recall 0.62, and Cohen's kappa 0.55, and the clean
holdout gives kappa 0.53. `--sample-for-labelling N --exclude <earlier.csv>`
regenerates a blank labeling sheet the way the two samples were drawn, with
`--seed` fixing the draw.

## Which script builds which display item

| Display item | Built by |
| --- | --- |
| Table 1, consensus recommendations | `main_text_tables.py` |
| Table 3, preparedness priorities | `priorities_table.py` |
| Table 4, panel characteristics | `r4_latex_tables.py` |
| Fig. 1, Delphi flow chart | `generate_delphi_flowchart.py` |
| Fig. 2, PRISMA flow diagram | `generate_prisma_flow.py` |
| Fig. 3, round flow chart | `generate_round_flow_chart.py` |
| Fig. 4, themes before and from 2020 | `lit_theme_synthesis.py --by-period` |
| Fig. 5, Round 3 versus Round 4 comparison | `r4_latex_tables.py` |
| Fig. 6, rankings by pandemic phase | `r4_latex_tables.py` |
| Agreement by statement origin, Discussion | `statement_origin_agreement.py` |
| Theme summary, SI | `lit_theme_synthesis.py` |
| Theme codebook, SI | `lit_theme_synthesis.py` |
| Study characteristics, SI | `lit_review_tables.py` |
| Rankings, SI | `r4_latex_tables.py` |
| Completers-only sensitivity, SI | `r4_sensitivity.py` |
| Revision mapping and statement provenance, SI | `statement_provenance.py` |
| Must-act recoding, SI | `mustact_recode.py` |
| Contributor disciplines, SI | `contributor_table.py` |
| Supplementary Data 1, included studies | `main_text_tables.py` |
| Supplementary Data 2, Round 4 statements | `r4_latex_tables.py` |

Five display items are hand-made, not computed. Table 2 (`theme_map.tex`) is
written by hand, `initial_statements.tex` is transcribed from the Round 1 panel
document, and the PRISMA and CREDES checklists are filled in by hand, so none of
these appears above and none is in this repository. `priorities_table.py` builds
Table 3, but its grouping and wording are the study team's.

`priorities_table.py` checks as well as builds. It reads the generated consensus
table back, compares it against `consensus_stats.json`, and refuses to write if
the two disagree. It also fails if a priority cites a statement ID absent from the
Round 4 ratings.

## Two steps are not deterministic

The full-text screen and the grouping of extracted items into eight candidate
themes both used a large language model, so neither reproduces byte for byte. Both
are frozen. `articles-full-screen-results.csv` is the screening run of record, and
the codebook is a fixed term list here. The deposit README documents how the
screen was validated. Everything downstream of them is deterministic.

## License and citing

Code here is MIT, see [LICENSE](LICENSE). The data deposit is CC BY-SA 4.0 except
for passages quoted from the screened publications, which its own README explains.

This repository is archived at [10.5281/zenodo.22233244](https://doi.org/10.5281/zenodo.22233244), which always
resolves to the newest release. Version v1.2.0, archived at [10.5281/zenodo.24562176](https://doi.org/10.5281/zenodo.24562176), produced the results in the paper.
Cite the paper for the findings, this DOI for the code, and
[10.5281/zenodo.22232255](https://doi.org/10.5281/zenodo.22232255) for the data.
See [CITATION.cff](CITATION.cff).
