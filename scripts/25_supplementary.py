#!/usr/bin/env python3
"""Phase 8: assemble the supplementary material referenced in the manuscript.

S1  search strategy: full strings, per-run hit counts, search log           (S1_search_strategy.md, S1_search_runs.csv)
S2  PRISMA 2020 checklist                                                    (scripts/23_prisma_checklist.py)
S3  extraction database and codebook                                         (S3_extraction_database.xlsx/.csv, S3_codebook.md)
S4  quality-assessment scores with justifications                           (S4_quality_assessment.csv)
S5  review protocol and dated amendment log                                  (S5_protocol.md)
S6  screening and full-text eligibility decisions                           (S6_*.csv)
Everything is copied from the project files; nothing is edited here.
"""
import csv
import shutil
from pathlib import Path

W = Path(__file__).resolve().parent.parent
OUT = W / "manuscript" / "supplementary"
OUT.mkdir(exist_ok=True)

s1 = ["# Supplementary S1. Search strategy", "",
      "Search conducted up to 13 November 2026: database search 7 October 2026; citation searching (one round, backward and "
      "forward, via OpenAlex) and a first update search 10 October 2026; second update search (same strings, no date filter) "
      "13 November 2026. Full strings, per-source hit counts and the search log follow.", "",
      (W / "logs" / "search_strings.md").read_text(), "", "## Search log", "", (W / "logs" / "search_log.md").read_text()]
(OUT / "S1_search_strategy.md").write_text("\n".join(s1))
shutil.copy(W / "stageB" / "search_runs.csv", OUT / "S1_search_runs.csv")
shutil.copy(W / "stageE" / "search_runs.csv", OUT / "S1_search_runs_update_2026-11-13.csv")

shutil.copy(W / "extraction" / "evidence_db.xlsx", OUT / "S3_extraction_database.xlsx")
shutil.copy(W / "extraction" / "evidence_db.csv", OUT / "S3_extraction_database.csv")
shutil.copy(W / "extraction" / "codebook.md", OUT / "S3_codebook.md")

R = list(csv.DictReader(open(W / "extraction" / "evidence_db.csv")))
with open(OUT / "S4_quality_assessment.csv", "w", newline="") as f:
    cols = ["study_id", "title", "year"] + [f"Q{i}" for i in range(1, 13)] + ["qa_total", "qa_band", "qa_note"]
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader(); w.writerows(R)

shutil.copy(W / "logs" / "protocol.md", OUT / "S5_protocol.md")

shutil.copy(W / "fulltext" / "fulltext_decisions.csv", OUT / "S6_fulltext_decisions.csv")
shutil.copy(W / "stageB" / "screening_decisions.csv", OUT / "S6_screening_decisions_database_records.csv")
with open(W / "stageA" / "stageA_inventory.csv") as fi, open(OUT / "S6_screening_decisions_seed_corpus.csv", "w", newline="") as fo:
    rd = csv.DictReader(fi)
    keep = ["study_id", "title", "authors", "year", "venue", "doi", "decision", "reason_code", "screening_note", "duplicate_of"]
    w = csv.DictWriter(fo, fieldnames=keep, extrasaction="ignore")
    w.writeheader(); w.writerows(rd)
shutil.copy(W / "stageB" / "records_unique.csv", OUT / "S6_database_records_unique.csv")
shutil.copy(W / "stageC" / "screening_decisions.csv", OUT / "S6_screening_decisions_citation_search.csv")
shutil.copy(W / "stageC" / "record_flow.json", OUT / "S6_citation_search_record_flow.json")
shutil.copy(W / "stageE" / "screening_decisions.csv", OUT / "S6_screening_decisions_update_search_2026-11-13.csv")
shutil.copy(W / "stageE" / "record_flow.json", OUT / "S6_update_search_2026-11-13_record_flow.json")

readme = """# Supplementary material

| File | Content |
|---|---|
| S1_search_strategy.md, S1_search_runs*.csv | Search strings, per-source hit counts (database search and second update search), search log (search up to 13 Nov 2026) |
| S2_PRISMA_2020_checklist.pdf/.md | PRISMA 2020 checklist with locations in the manuscript |
| S3_extraction_database.xlsx/.csv, S3_codebook.md | Extraction record of every included study and the codebook |
| S4_quality_assessment.csv | Q1-Q12 scores, totals, bands and justification of every score below 2 |
| S5_protocol.md | Review protocol with the dated amendment log |
| S6_*.csv, S6_*_record_flow.json | Title/abstract screening decisions (seed corpus, database records, citation-search records and second-update-search records), record flows of citation searching and the second update search, and full-text eligibility decisions (all stages) |
"""
(OUT / "README.md").write_text(readme)
print("supplementary files:", sorted(p.name for p in OUT.iterdir() if not p.name.startswith("S2_PRISMA_2020_checklist.") or p.suffix in (".pdf", ".md")))
