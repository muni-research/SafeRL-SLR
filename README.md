# Safe Reinforcement Learning for Autonomous Vehicles: systematic review, code and data

Code and data behind the PRISMA 2020 systematic review *Safe Reinforcement Learning for Autonomous Vehicles:
A Systematic Review of Methods, Safety Assurance, Applications, and Future Directions* (submitted to
*Artificial Intelligence Review*). The review includes 702 studies (711 reports); the search was
conducted up to 13 November 2026.

Every count, table, figure and number in the article is computed by the scripts in `scripts/` from the records and
the extraction database in this repository; nothing is typed in by hand.

## Contents
| Path | Content |
|---|---|
| `scripts/` | The full pipeline, numbered in run order (search, merging, screening, full-text eligibility, extraction, analysis, figures, tables) |
| `logs/` | Protocol with dated amendment log, search strings, search log and report, PRISMA counts, DOI audit, results of the human consistency checks (`consistency/`) |
| `stageA/` | Seed corpus inventory (supplied articles) |
| `stageB/` | Database search: per-query hit counts (`search_runs.csv`), unique records, duplicate log, screening decisions, recall check |
| `stageC/` | Citation searching (backward and forward, OpenAlex) and first update search: candidates, record flow, screening and full-text decisions |
| `stageE/` | Second update search (13 November 2026): candidates, run log, record flow, decisions and extraction records |
| `stageD/journal_quartiles.csv` | Journal quartile per included study (used only to choose example studies for the tables) |
| `fulltext/` | Full-text retrieval status and eligibility decisions with exclusion codes |
| `extraction/` | Extraction database (`evidence_db.csv`/`.xlsx`, one record per included study with the 12-item quality scores and their justifications), codebook, raw extraction records, explainability codes |
| `analysis/` | Generated statistics (`stats_summary.md`, `stats.json`, `tables/`) |
| `manuscript/` | Article source (`main.tex`; scripts 20-21 write the tables and numbers into it), bibliographies and generated figures |

Abstracts and keywords are removed from the record files (they are copied from bibliographic databases); titles,
DOIs and identifiers are kept so that every decision can be traced.

## Reproducing the analysis
Python 3.10 or later; `pip install -r requirements.txt`.

```
python3 scripts/10_prisma.py          # PRISMA 2020 counts (both columns of the flow diagram)
python3 scripts/15_stats.py           # all statistics and analysis tables
python3 scripts/18_figures.py         # figures (manuscript/figures/)
python3 scripts/20_tables.py          # manuscript tables, written into manuscript/main.tex
python3 scripts/21_text_numbers.py    # every number used in the text, as LaTeX macros
```
These steps need no network access and reproduce the published counts exactly.

## Re-running the literature searches (OpenAlex and arXiv)
The searches use the free OpenAlex and arXiv APIs; no key is required.

```
export SLR_CONTACT_EMAIL=you@example.org   # optional: OpenAlex "polite pool" contact address
python3 scripts/05_search.py openalex arxiv  # database search: queries and hit counts -> stageB/search_runs.csv
python3 scripts/06_merge.py                  # merge, de-duplicate (DOI, normalized title, author, year)
python3 scripts/24_snowball_update.py        # backward/forward citation searching and first update search
python3 scripts/33_update_search.py          # second update search (all years, de-duplicated against all handled records)
```
The exact query strings are in `scripts/05_search.py` and `logs/search_strings.md`, and the hit counts obtained on
each run date are in `stageB/search_runs.csv`, `stageC/run_log.txt` and `stageE/search_runs.csv`. OpenAlex updates its
index continuously, so re-running a query today returns somewhat different hit counts; the records actually screened
in the review are the ones stored in `stageB/`, `stageC/` and `stageE/`. Raw API responses are not included (size);
the scripts recreate them. Scripts that read full-text PDFs (01-03, 08-08c, 11-13b, 16-17, 26-27) need the PDFs,
which are not redistributed for copyright reasons; their outputs are included.

## Licence
Code (`scripts/`): MIT License (`LICENSE`). Data and documentation: Creative Commons Attribution 4.0 International
(CC BY 4.0, `LICENSE-DATA.md`). Bibliographic metadata of the included studies remains subject to the terms of its sources.

## Citation
If you use this code or data, please cite the article (citation will be added on publication).
