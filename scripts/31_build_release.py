#!/usr/bin/env python3
"""Phase 8: assemble a local, publishable copy of the review's code and data (nothing is uploaded).

Writes ../Release_Repository/ next to SLR_Workspace with the scripts, the extraction database and codebook,
screening and eligibility decisions, PRISMA counts, search logs and generated statistics. Excluded on
purpose: full-text PDFs and extraction packets/dossiers (publisher copyright), abstracts (copied from
bibliographic records; the columns are dropped), raw API caches (large; regenerable with scripts 05/24),
the consistency-check keys (released after the checks) and internal notes on the Sample Article.
"""
import csv
import shutil
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)
W = Path(__file__).resolve().parent.parent
OUT = W.parent / "Release_Repository"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()


def cp(src, dst=None):
    s = W / src
    d = OUT / (dst or src)
    d.parent.mkdir(parents=True, exist_ok=True)
    if s.is_dir():
        shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc",
                                                     "35_ieee_search.py",    # IEEE coverage check: not reported (authors, 17 Nov)
                                                     "08d_chrome_fetch.py")) # drove the authors' browser for paywalled PDFs; not needed to reproduce
    else:
        shutil.copy2(s, d)


def cp_csv_without(src, drop=("abstract",)):
    s, d = W / src, OUT / src
    d.parent.mkdir(parents=True, exist_ok=True)
    with open(s, newline="") as fi, open(d, "w", newline="") as fo:
        r = csv.DictReader(fi)
        keep = [c for c in r.fieldnames if c not in drop]
        w = csv.DictWriter(fo, fieldnames=keep, extrasaction="ignore")
        w.writeheader(); w.writerows(r)


cp("scripts")
for f in ("codebook.md", "evidence_db.csv", "evidence_db.xlsx", "xai_codes.csv", "raw"):
    cp(f"extraction/{f}")
cp_csv_without("stageA/stageA_inventory.csv", drop=("abstract", "keywords"))
for f in ("screening_decisions.csv", "search_runs.csv", "duplicate_log.csv", "study_ids.csv", "recall_check.txt"):
    cp(f"stageB/{f}")
cp_csv_without("stageB/records_unique.csv")
cp_csv_without("stageB/records_all.csv")
cp_csv_without("fulltext/needs_institutional_access.csv", drop=("save_as",))   # reasons for reports not retrieved                     # all database records before de-duplication (PRISMA)
# journal quartiles: only what 20_tables.py uses (JCR names and impact factors are Clarivate data, not redistributed)
cp_csv_without("stageD/journal_quartiles.csv", drop=("jcr_name", "jif"))
# human consistency checks: screening check (completed) and the summary used in the text; the extraction-check key is
# withheld until that check is complete, so that it cannot be seen by the second coder
for f in ("consistency_results.json", "consistency_results.txt", "screening_sample_key.csv"):
    cp(f"logs/consistency/{f}")
for f in ("screening_decisions.csv", "record_flow.json", "run_log.txt", "retrieval_status.csv", "decisions", "ft_decisions_raw"):
    cp(f"stageC/{f}")
cp_csv_without("stageC/candidates.csv")
cp_csv_without("stageC/records.csv")
for f in ("screening_decisions.csv", "record_flow.json", "run_log.txt", "search_runs.csv", "retrieval_status.csv",
          "decisions", "ft_decisions_raw", "extraction"):            # second update search (2026-11-13)
    cp(f"stageE/{f}")
cp_csv_without("stageE/candidates.csv")
cp_csv_without("stageE/records.csv")
for f in ("fulltext_decisions.csv", "retrieval_status.csv"):
    cp(f"fulltext/{f}")
for f in ("protocol.md", "search_strings.md", "search_log.md", "search_report.md", "prisma_counts.txt",
          "doi_audit.csv", "doi_audit_summary.txt", "similarity_check.txt"):
    cp(f"logs/{f}")
cp("analysis/stats_summary.md"); cp("analysis/stats.json"); cp("analysis/tables")
cp("manuscript/figures"); cp("manuscript/generated"); cp("manuscript/main.tex"); cp("manuscript/stats_macros.tex")
for f in ("references.bib", "included_studies.bib"):
    if (W / "manuscript" / f).exists():
        cp(f"manuscript/{f}")

P = __import__("json").loads((W / "manuscript" / "generated" / "prisma_counts.json").read_text())
INC = P["included"]
(OUT / "README.md").write_text(f"""# Safe Reinforcement Learning for Autonomous Vehicles: systematic review, code and data

Code and data behind the PRISMA 2020 systematic review *Safe Reinforcement Learning for Autonomous Vehicles:
A Systematic Review of Methods, Safety Assurance, Applications, and Future Directions* (submitted to
*Artificial Intelligence Review*). The review includes {INC["studies"]} studies ({INC["reports"]} reports); the search was
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
""")
(OUT / "LICENSE").write_text("""MIT License

Copyright (c) 2026 The authors of "Safe Reinforcement Learning for Autonomous Vehicles: A Systematic Review"

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
""")
(OUT / "LICENSE-DATA.md").write_text("""# Data licence

The data and documentation in this repository (everything outside `scripts/`) are licensed under the
Creative Commons Attribution 4.0 International License (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/
""")
(OUT / "requirements.txt").write_text("matplotlib>=3.8\nnumpy>=1.24\nopenpyxl>=3.1\npymupdf>=1.23  # only for the scripts that read full-text PDFs\n")
(OUT / ".gitignore").write_text("__pycache__/\n*.pyc\n.DS_Store\n*.aux\n*.log\n*.fls\n*.fdb_latexmk\n*.synctex.gz\n*.out\n*.blg\n")
n = sum(1 for _ in OUT.rglob("*") if _.is_file())
size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) / 1e6
print(f"wrote {OUT} ({n} files, {size:.1f} MB)")
