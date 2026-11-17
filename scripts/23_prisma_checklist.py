#!/usr/bin/env python3
"""Phase 8: PRISMA 2020 checklist (Supplementary Table S2).

Each checklist item is mapped to the labels of main.tex where it is reported; section/table/figure numbers
and pages are read from manuscript/main.aux, so the checklist stays correct when the manuscript changes.
Item topics follow the PRISMA 2020 checklist (Page et al. 2021); the wording here is a short paraphrase.
Output: manuscript/supplementary/S2_PRISMA_2020_checklist.md and .tex (compiled to .pdf).
"""
import re
import subprocess
from pathlib import Path

W = Path(__file__).resolve().parent.parent
AUX = (W / "manuscript" / "main.aux").read_text()
LAB = {m.group(1): (m.group(2), m.group(3)) for m in
       re.finditer(r"\\newlabel\{([^}]*)\}\{\{([^}]*)\}\{([^}]*)\}", AUX)}
KIND = {"sec": "Sect.", "tab": "Table", "fig": "Fig."}


def loc(*labels, extra=""):
    out = []
    for l in labels:
        num, page = LAB[l]
        out.append(f"{KIND[l.split(':')[0]]} {num} (p. {page})")
    return "; ".join(out) + (f"; {extra}" if extra else "")


ITEMS = [
    ("TITLE", "1", "Identify the report as a systematic review", "Title page (p. 1)"),
    ("ABSTRACT", "2", "Structured summary following the PRISMA 2020 for Abstracts items", "Abstract (p. 1); unstructured, as usual for the journal: covers objectives, sources and date, number of studies, synthesis, main results and implications; registration and funding not stated"),
    ("INTRODUCTION", "3", "Rationale in the context of existing knowledge", loc("sec:intro", "tab:priorreviews")),
    ("", "4", "Objectives or questions the review addresses", loc("sec:rqs", "tab:rqs")),
    ("METHODS", "5", "Eligibility criteria and how studies were grouped for synthesis", loc("sec:method", "tab:criteria")),
    ("", "6", "Information sources and the date each was last searched", loc("sec:search", "tab:search", extra="search up to 7 Oct 2026")),
    ("", "7", "Full search strategies for all databases", loc("sec:search", "tab:search", extra="Supplementary Table S1")),
    ("", "8", "Selection process (reviewers, independence, automation tools)", loc("sec:dedup", extra="Use of AI assistance, Sect. 3")),
    ("", "9", "Data collection process", loc("sec:method", extra="Data extraction subsection")),
    ("", "10a", "Outcomes for which data were sought", loc("sec:method", "tab:qa", extra="extraction fields; Supplementary S3")),
    ("", "10b", "Other variables for which data were sought", loc("sec:method", extra="codebook, Supplementary S3")),
    ("", "11", "Study risk-of-bias (quality) assessment", loc("sec:method", "tab:qa")),
    ("", "12", "Effect measures", "Not applicable: no pooled effect estimates; descriptive frequencies only (Synthesis methods, Sect. 3)"),
    ("", "13a", "Processes to decide which studies were eligible for each synthesis", loc("sec:method", extra="Synthesis methods")),
    ("", "13b", "Methods to prepare data for synthesis", loc("sec:method", extra="Synthesis methods; scripts in code repository")),
    ("", "13c", "Methods to tabulate or display results", loc("sec:method", extra="Synthesis methods")),
    ("", "13d", "Methods to synthesise results and rationale", loc("sec:method", extra="Synthesis methods (no meta-analysis, reasons given)")),
    ("", "13e", "Methods to explore heterogeneity", loc("sec:method", extra="cross-tabulations by task, mechanism, period")),
    ("", "13f", "Sensitivity analyses", loc("sec:biblio", extra="Robustness of the findings")),
    ("", "14", "Reporting-bias assessment", loc("sec:validity", extra="external validity, retrieval-round comparison in Sect. 4")),
    ("", "15", "Certainty (strength) of evidence assessment", loc("sec:levels", "tab:levels", extra="review-derived evidence levels and readiness chain, Sect. 12")),
    ("RESULTS", "16a", "Results of the search and selection, with flow diagram", loc("sec:biblio", "fig:prisma")),
    ("", "16b", "Studies that seemed eligible but were excluded, with reasons", loc("fig:prisma", extra="full-text exclusion reasons; Supplementary S3")),
    ("", "17", "Characteristics of included studies", loc("sec:biblio", "tab:framework", extra="Supplementary S3 (extraction database)")),
    ("", "18", "Risk of bias (quality) in studies", loc("tab:quality", extra="per-study scores in Supplementary S4")),
    ("", "19", "Results of individual studies", "Supplementary S3 (per-study extraction records); examples cited in Tables 8-22"),
    ("", "20a", "Characteristics and risk of bias of studies contributing to each synthesis", loc("tab:mechanisms", "tab:applications")),
    ("", "20b", "Results of all syntheses", loc("sec:taxonomy", "sec:integration", "sec:apps", "sec:uncertainty", "sec:eval", "sec:xai", "sec:simreal", "sec:framework")),
    ("", "20c", "Investigations of heterogeneity", loc("tab:applications", "tab:readinesstasks", "fig:evolution")),
    ("", "20d", "Sensitivity analyses", loc("sec:biblio", extra="Robustness of the findings")),
    ("", "21", "Reporting biases", loc("sec:biblio", extra="retrieval-round comparison; Sect. 15")),
    ("", "22", "Certainty (strength) of evidence", loc("sec:framework", "fig:chain", "tab:framework")),
    ("DISCUSSION", "23a", "Interpretation in the context of other evidence", loc("sec:discussion")),
    ("", "23b", "Limitations of the evidence", loc("sec:discussion", "sec:gaps")),
    ("", "23c", "Limitations of the review processes", loc("sec:validity")),
    ("", "23d", "Implications for practice, policy and research", loc("sec:gaps", "tab:roadmap", "sec:conclusion")),
    ("OTHER", "24a", "Registration information", "PENDING: authors to state registration or its absence (Sect. 3)"),
    ("", "24b", "Where the protocol can be accessed", "Protocol and amendment log in supplementary material (Sect. 3)"),
    ("", "24c", "Amendments to the protocol", "Dated amendment log in supplementary material (Sect. 3)"),
    ("", "25", "Support (funding)", "Declarations (PENDING: authors)"),
    ("", "26", "Competing interests", "Declarations (PENDING: authors)"),
    ("", "27", "Availability of data, code and other materials", "Declarations: data in supplementary material; code repository (PENDING link)"),
]

out = W / "manuscript" / "supplementary"
out.mkdir(exist_ok=True)
md = ["# Supplementary Table S2. PRISMA 2020 checklist", "",
      "Locations refer to the manuscript (section, table or figure number and page). Generated by "
      "`scripts/23_prisma_checklist.py` from `main.aux`.", "",
      "| Section | Item | Checklist topic | Location in manuscript |", "|---|---|---|---|"]
md += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in ITEMS]
(out / "S2_PRISMA_2020_checklist.md").write_text("\n".join(md) + "\n")


def tex_esc(s):
    return s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


rows = "\n".join(f"{tex_esc(a)} & {b} & {tex_esc(c)} & {tex_esc(d)} \\\\" for a, b, c, d in ITEMS)
tex = r"""\documentclass[10pt]{article}
\usepackage[a4paper,margin=2cm]{geometry}
\usepackage{longtable,booktabs,array}
\begin{document}
\noindent\textbf{Supplementary Table S2.} PRISMA 2020 checklist for \emph{Safe Reinforcement Learning for
Autonomous Vehicles: A Systematic Review of Methods, Safety Assurance, Applications, and Future Directions}.
Locations give the section, table or figure number and page in the manuscript. Item topics follow the PRISMA 2020
checklist (Page et al.\ 2021, BMJ 372:n71) in shortened form.\par\medskip
\small
\begin{longtable}{@{}p{2.1cm}p{0.8cm}p{6.4cm}p{6.4cm}@{}}
\toprule
Section & Item & Checklist topic & Location in manuscript\\ \midrule\endhead
""" + rows + r"""
\bottomrule
\end{longtable}
\end{document}
"""
(out / "S2_PRISMA_2020_checklist.tex").write_text(tex)
subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "S2_PRISMA_2020_checklist.tex"], cwd=out,
               capture_output=True)
pend = sum("PENDING" in x[3] for x in ITEMS)
print(f"{len(ITEMS)} checklist items written; {pend} pending author input")
