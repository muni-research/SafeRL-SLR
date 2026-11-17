"""Compute all PRISMA 2020 counts from the logged data (Stage A + Stage B) and write logs/prisma_counts.txt.
Also writes manuscript/generated/prisma_counts.json for the PRISMA figure.
Run after 04_build_inventory.py, 06_merge.py and 09_compile_screening.py (and later the full-text step).
"""
import csv, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = Path(__file__).resolve().parent.parent
A = list(csv.DictReader(open(W / "stageA" / "stageA_inventory.csv")))
recs_all = list(csv.DictReader(open(W / "stageB" / "records_all.csv")))
uniq = list(csv.DictReader(open(W / "stageB" / "records_unique.csv")))
scrB = list(csv.DictReader(open(W / "stageB" / "screening_decisions.csv")))
src = Counter(r["source"] for r in recs_all)

a_id = len(A); a_dup = sum(r["decision"] == "Duplicate" for r in A)
b_id = len(recs_all); b_dup_internal = b_id - len(uniq)
b_overlap_A = sum(bool(u["in_stageA"]) for u in uniq)
b_dup_A_manual = sum(r["decision"] == "Duplicate" for r in scrB)
total_id = a_id + b_id
total_dup = a_dup + b_dup_internal + b_overlap_A + b_dup_A_manual
screened = [r for r in A if r["decision"] != "Duplicate"] + [r for r in scrB if r["decision"] != "Duplicate"]
assert len(screened) == total_id - total_dup
c = Counter(r["decision"] for r in screened)
exc = Counter(r["reason_code"] for r in screened if r["decision"] in ("Exclude", "Background"))
sought = c["Include"] + c["Unsure"]
ft = {}
ftf = W / "fulltext" / "retrieval_status.csv"
if ftf.exists():
    st = list(csv.DictReader(open(ftf)))
    ft["not_retrieved"] = sum(r["status"] == "NOT RETRIEVED" for r in st)
    acc = W / "fulltext" / "needs_institutional_access.csv"   # reason labels recorded during retrieval
    if acc.exists():
        lab = {r["study_id"]: r["Downloaded"] for r in csv.DictReader(open(acc))}
        ft["not_retrieved_by_reason"] = dict(Counter(lab.get(r["study_id"], "not recorded")
                                                     for r in st if r["status"] == "NOT RETRIEVED").most_common())
fd = {}
fdf = W / "fulltext" / "fulltext_decisions.csv"
dall = list(csv.DictReader(open(fdf))) if fdf.exists() else []
dC = [r for r in dall if r["study_id"].startswith("C")]          # citation-search reports (Phase 8)
dE = [r for r in dall if r["study_id"].startswith("E")]          # second update search (2026-11-13)
if fdf.exists():
    d = [r for r in dall if not r["study_id"].startswith(("C", "E"))]
    fd = {"assessed": len(d),
          "excluded": sum(r["ft_decision"] in ("Exclude", "Background") for r in d),
          "excluded_by_reason": dict(sorted(Counter(r["reason_code"] for r in d if r["ft_decision"] in ("Exclude", "Background")).items())),
          "additional_reports_of_included_studies": sum(r["ft_decision"] == "Additional report" for r in d),
          "studies_included": sum(r["ft_decision"] == "Include" for r in d)}

# ---- identification via other methods: citation searching + update search (Phase 8, 2026-10-10)
oth = {}
SC = W / "stageC"
if (SC / "record_flow.json").exists() and dC:
    flow = json.load(open(SC / "record_flow.json"))
    runlog = (SC / "run_log.txt").read_text()
    import re as _re
    nb = int(_re.search(r"backward: \d+ referenced works, (\d+) retrieved", runlog).group(1))
    nf = int(_re.search(r"forward: (\d+) citing works", runlog).group(1))
    nu = sum(int(x) for x in _re.findall(r"update OA-\w+: (\d+) records", runlog))
    scC = list(csv.DictReader(open(SC / "screening_decisions.csv")))
    cc = Counter(r["decision"] for r in scC)
    excC = Counter(r["code"] for r in scC if r["decision"] == "Exclude")
    stC = list(csv.DictReader(open(SC / "retrieval_status.csv")))
    oth = {"records_identified": flow["raw"], "backward": nb, "forward": nf, "update_search": nu,
           "duplicates_removed": flow["already_screened"] + flow["duplicate_within_citation_results"],
           "duplicates_already_screened": flow["already_screened"],
           "duplicates_within_citation_results": flow["duplicate_within_citation_results"],
           "removed_by_automation_keyword_filter": flow["keyword_filter"],
           "records_screened": len(scC), "duplicates_found_at_screening": cc["Duplicate"],
           "records_excluded": cc["Exclude"] + cc["Background"], "of_which_background_pool_EC1": cc["Background"],
           "screening_excluded_by_reason": dict(sorted((Counter(excC) + Counter({"EC1": cc["Background"]})).items())),
           "reports_sought": cc["Include"] + cc["Unsure"],
           "not_retrieved": sum(r["status"] == "not retrieved" for r in stC),
           "assessed": len(dC),
           "excluded": sum(r["ft_decision"] in ("Exclude", "Background") for r in dC),
           "fulltext_excluded_by_reason": dict(sorted(Counter(r["reason_code"] for r in dC if r["ft_decision"] in ("Exclude", "Background")).items())),
           "additional_reports": sum(r["ft_decision"] == "Additional report" for r in dC),
           "studies_included": sum(r["ft_decision"] == "Include" for r in dC)}

# ---- second update search (2026-11-13): same strings as the database search, no date filter, de-duplicated against
# every record already handled; reported in the 'other methods' column together with the first update search
SE = W / "stageE"
upd2 = {}
if oth and (SE / "record_flow.json").exists() and (SE / "screening_decisions.csv").exists():
    flE = json.load(open(SE / "record_flow.json"))
    scE = list(csv.DictReader(open(SE / "screening_decisions.csv")))
    ce = Counter(r["decision"] for r in scE)
    excE = Counter(r["code"] for r in scE if r["decision"] == "Exclude")
    soughtE = ce["Include"] + ce["Unsure"]
    # retrieved = PDF on disk (workspace); the public release has no PDFs and reads the 'retrieved' column instead,
    # which is synchronised here from the PDFs whenever they are present
    rsE = SE / "retrieval_status.csv"
    rowsE = list(csv.DictReader(open(rsE))) if rsE.exists() else []
    pdfsE = {p.stem for p in (SE / "fulltext").glob("E*.pdf")} if (SE / "fulltext").exists() else None
    if pdfsE is not None:
        retrievedE = pdfsE
        if rowsE:
            for r in rowsE:
                r["retrieved"] = "yes" if r["eid"] in pdfsE else "no"
            with open(rsE, "w", newline="") as fo:
                w = csv.DictWriter(fo, fieldnames=list(rowsE[0].keys())); w.writeheader(); w.writerows(rowsE)
    else:
        retrievedE = {r["eid"] for r in rowsE if r["retrieved"] == "yes"}
    upd2 = {"date": flE["date"], "records_identified": flE["raw"],
            "duplicates_removed": flE["already_handled"] + flE["duplicate_within_update"],
            "duplicates_already_screened": flE["already_handled"], "duplicates_within_update": flE["duplicate_within_update"],
            "removed_by_automation_keyword_filter": flE["keyword_filter"], "records_screened": len(scE),
            "records_excluded": ce["Exclude"] + ce["Background"], "of_which_background_pool_EC1": ce["Background"],
            "screening_excluded_by_reason": dict(sorted((excE + Counter({"EC1": ce["Background"]})).items())),
            "reports_sought": soughtE, "not_retrieved": soughtE - len(retrievedE), "assessed": len(dE),
            "excluded": sum(r["ft_decision"] in ("Exclude", "Background") for r in dE),
            "fulltext_excluded_by_reason": dict(sorted(Counter(r["reason_code"] for r in dE if r["ft_decision"] in ("Exclude", "Background")).items())),
            "additional_reports": sum(r["ft_decision"] == "Additional report" for r in dE),
            "studies_included": sum(r["ft_decision"] == "Include" for r in dE)}
    oth["update_search_2"] = upd2["records_identified"]
    for k in ("records_identified", "duplicates_removed", "duplicates_already_screened", "removed_by_automation_keyword_filter",
              "records_screened", "records_excluded", "of_which_background_pool_EC1", "reports_sought", "not_retrieved",
              "assessed", "excluded", "additional_reports", "studies_included"):
        oth[k] += upd2[k]
    oth["duplicates_within_citation_results"] += upd2["duplicates_within_update"]
    oth["screening_excluded_by_reason"] = dict(sorted((Counter(oth["screening_excluded_by_reason"]) + Counter(upd2["screening_excluded_by_reason"])).items()))
    oth["fulltext_excluded_by_reason"] = dict(sorted((Counter(oth["fulltext_excluded_by_reason"]) + Counter(upd2["fulltext_excluded_by_reason"])).items()))

out = {
  "identification": {"records_supplied_corpus": a_id, "records_databases_total": b_id,
                     "records_by_database": dict(src),
                     "duplicates_removed_total": total_dup,
                     "duplicates_detail": {"within_supplied_corpus": a_dup, "within_database_results": b_dup_internal,
                                           "database_records_already_in_supplied_corpus": b_overlap_A,
                                           "found_manually_at_screening": b_dup_A_manual}},
  "screening": {"records_screened": len(screened), "records_excluded": c["Exclude"] + c["Background"],
                "excluded_by_reason": dict(sorted(exc.items())),
                "of_which_background_pool_EC1": c["Background"]},
  "eligibility": {"reports_sought_for_retrieval": sought, "include_at_title_abstract": c["Include"],
                  "unsure_at_title_abstract": c["Unsure"], **ft, **{f"fulltext_{k}": v for k, v in fd.items()}},
  "other_methods": oth,
  "update_search_2": upd2,
  "included": {"studies": (fd.get("studies_included") or 0) + oth.get("studies_included", 0),
               "reports": (fd.get("studies_included") or 0) + (fd.get("additional_reports_of_included_studies") or 0)
                          + oth.get("studies_included", 0) + oth.get("additional_reports", 0),
               "studies_databases": fd.get("studies_included"), "studies_other_methods": oth.get("studies_included", 0),
               "status": "final (database retrieval closed 2026-10-09; citation searching 2026-10-10; second update search 2026-11-13)"},
}
txt = ["# PRISMA 2020 counts — generated by scripts/10_prisma.py (do not edit by hand)",
       "# Search conducted up to 2026-11-13 (database search 2026-10-07; citation searching and first update search 2026-10-10; second update search 2026-11-13)", ""]
txt += ["IDENTIFICATION",
        f"  Records from supplied corpus (Stage A): {a_id}",
        f"  Records from databases (Stage B): {b_id}  " + ", ".join(f"{k}={v}" for k, v in sorted(src.items())),
        f"  Duplicate records removed: {total_dup}  (supplied corpus {a_dup}; across database results {b_dup_internal}; "
        f"database records already in supplied corpus {b_overlap_A}; found manually at screening {b_dup_A_manual})", "",
        "SCREENING",
        f"  Records screened (title/abstract): {len(screened)}",
        f"  Records excluded: {c['Exclude'] + c['Background']}"]
txt += [f"    {k}: {v}" for k, v in sorted(exc.items())]
txt += ["", "ELIGIBILITY",
        f"  Reports sought for retrieval: {sought}  (Include {c['Include']}, Unsure {c['Unsure']})",
        f"  Reports not retrieved: {ft.get('not_retrieved', 'pending (full-text retrieval not yet run)')}"]
# per-publisher reasons are kept in prisma_counts.json and the methods text only (user decision 2026-10-09)
txt += [        f"  Reports assessed for eligibility: {fd.get('assessed', 'pending')}",
        f"  Reports excluded: {fd.get('excluded', 'pending')}"]
txt += [f"    {k}: {v}" for k, v in fd.get("excluded_by_reason", {}).items()]
txt += ["", "INCLUDED (final; full-text retrieval closed 2026-10-09)",
        f"  Studies included: {fd.get('studies_included', 'pending')}",
        f"  Reports of included studies: {(fd.get('studies_included') or 0) + (fd.get('additional_reports_of_included_studies') or 0)} "
        f"(incl. {fd.get('additional_reports_of_included_studies', 0)} additional conference/preprint reports)"]
if oth:
    txt += ["", "IDENTIFICATION VIA OTHER METHODS (citation searching + update search, 2026-10-10; second update search, 2026-11-13)",
            f"  Records identified: {oth['records_identified']}  (backward {oth['backward']}, forward {oth['forward']}, update search {oth['update_search']}, second update search {oth.get('update_search_2', 0)})",
            f"  Duplicate records removed: {oth['duplicates_removed']}  (already screened in the database search {oth['duplicates_already_screened']}; within citation results {oth['duplicates_within_citation_results']})",
            f"  Records removed by automation tool (RL AND safety AND road-vehicle keyword filter): {oth['removed_by_automation_keyword_filter']}",
            f"  Records screened: {oth['records_screened']}; duplicates found at screening {oth['duplicates_found_at_screening']}; excluded {oth['records_excluded']}"]
    txt += [f"    {k}: {v}" for k, v in oth["screening_excluded_by_reason"].items()]
    txt += [f"  Reports sought: {oth['reports_sought']}; not retrieved: {oth['not_retrieved']}; assessed: {oth['assessed']}; excluded: {oth['excluded']}"]
    txt += [f"    {k}: {v}" for k, v in oth["fulltext_excluded_by_reason"].items()]
    txt += [f"  Studies included: {oth['studies_included']} (+{oth['additional_reports']} additional reports)",
            "", f"TOTAL STUDIES INCLUDED: {out['included']['studies']}  (reports {out['included']['reports']})"]
(W / "logs" / "prisma_counts.txt").write_text("\n".join(txt) + "\n")
(W / "manuscript" / "generated").mkdir(parents=True, exist_ok=True)
(W / "manuscript" / "generated" / "prisma_counts.json").write_text(json.dumps(out, indent=1))
print("\n".join(txt))
