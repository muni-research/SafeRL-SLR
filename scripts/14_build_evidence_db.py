"""Phase 4 step 2: build the evidence database from the raw extraction records.

Reads extraction/raw/batch*.txt (codebook format, see extraction/codebook.md §12), validates every
coded field against the controlled vocabularies, merges bibliographic fields from the inventories,
computes QA totals/bands and the derived CLAUDE.md §17 RL-role category.
Outputs: extraction/evidence_db.csv, extraction/evidence_db.xlsx (Evidence, QA, Codebook-check sheets)
Exit status 1 if any record fails validation (the problems are printed).
"""
import csv, re, sys
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

ROOT = Path(__file__).resolve().parents[2]
W = Path(__file__).resolve().parent.parent
X = W / "extraction"

V = {  # controlled vocabularies (codebook v1.1); multi-valued fields separated by ';'
    "task": "LK LC MERGE OVT CF INT RAB CA EMG PED NAV MP TD PLT COOP RACE PARK E2E",
    "scenario": "HWY URB INTX RAMP RAB RURAL TRACK PARKLOT MIXED GENERIC",
    "traffic": "NONE SCRIPTED REPLAY LEARNED HUMAN MIXED",
    "rl_paradigm": "MF MB OFF OFF2ON IL+RL HRL META LLM+RL",
    "agents": "SA MA-CEN MA-CTDE MA-DEC",
    "network": "MLP CNN RNN GNN ATT RBF NR",
    "obs_type": "VEC IMG BEV LIDAR GRAPH OCC LANG NR",
    "action_type": "DISC CONT HYB NR",
    "action_level": "CTRL TRAJ BEHAV PARAM MIXED NR",
    "mech": "A B C D E F G H I J K L M N O P Q R S T U V W X",
    "mech_primary": "A B C D E F G H I J K L M N O P Q R S T U V W X",
    "mech_stage": "TRAIN EXEC BOTH",
    "rl_output": "ACT DEC PARAM TRAJ RES",
    "safety_integration": "NONE FILTER CORRECT EMBED MASK",
    "control": "NONE PID PP STANLEY LQR MPC QP IDM MOBIL SMC APF PLANNER BACKSTEP RULE",
    "safety_claim": "EMP STAT PROB CEXP ROB FORMAL RT CERT",
    "safety_level": "L0 L1 L2 L3 L4 L5",
    "uncertainty": "EPI ALE SENS INTENT MODEL PRED DSHIFT PO STOCH ADV DIST NONE",
    "simulator": "CARLA SUMO HWENV METADRIVE SMARTS FLOW TORCS AIRSIM LGSVL CARSIM PRESCAN SIMULINK GAZEBO WEBOTS UNITY NUPLAN WAYMAX COMMONROAD SAFETYGYM BULLET CUSTOM NR",
    "dataset": "NGSIM HIGHD IND ROUND EXID INTERACTION WAYMO NUSCENES NUPLAN ARGOVERSE OWN NONE",
    "vehicle_model": "PM KIN DYN SIMVEH REAL NR",
    "metrics": "COLL SUCC VIOL TTC PET DIST RISK INTERV UNSAFE OFFROAD RULE DEV JERK ACC COMF DSCORE REW SPEED TIME THRU ENERGY SAMPLE COMP GEN",
    "baseline_types": "NSRL SRL CLASS HUMAN ABL NONE",
    "generalization": "DENS GEOM WEATHER UNSEEN AGENTS DIST DYN DOMAIN S2R RULES NONE",
    "validation_tier": "SIM-LOW SIM-HIFI SIM-DATA HIL SCALED CLOSED ROAD DEPLOY",
    "code": "Y REQ N",
    "data_avail": "Y N NA",
    "hyperparams": "Y P N",
    "eval_protocol": "Y P N",
    "stats": "Y P N",
    "compute": "Y N",
    "stack": "PERC PRED PLAN DEC CTRL SUPERV RTA",
}
V = {k: set(v.split()) for k, v in V.items()}
SINGLE = {"traffic", "agents", "action_type", "action_level", "mech_primary", "mech_stage", "rl_output",
          "safety_integration", "safety_level", "vehicle_model", "validation_tier", "code", "data_avail",
          "hyperparams", "eval_protocol", "stats", "compute"}
FIELDS = ["country", "problem", "task", "scenario", "traffic", "rl_paradigm", "agents", "n_agents", "algorithm",
          "method_name", "network", "obs_type", "action_type", "action_level", "reward", "safety_cost", "constraints",
          "mech", "mech_primary", "mech_stage", "rl_output", "safety_integration", "control", "safety_claim",
          "guarantee_assumptions", "safety_level", "level_note", "uncertainty", "uncertainty_method", "simulator",
          "dataset", "vehicle_model", "metrics", "baselines", "baseline_types", "results", "generalization",
          "validation_tier", "real_world", "code", "code_url", "data_avail", "hyperparams", "seeds", "eval_protocol",
          "stats", "compute", "stack", "limitations", "qa", "qa_note"]
# vehicle_model may legitimately list two models (simulation + real); allow multi there
SINGLE.discard("vehicle_model")
ROLE = {"ACT": "1 RL generates control action", "RES": "1 RL generates control action",
        "DEC": "2 RL generates high-level decision", "TRAJ": "2 RL generates high-level decision",
        "PARAM": "3 RL provides controller parameters"}
INTEG = {"FILTER": "4 RL under a safety filter", "MASK": "4 RL under a safety filter",
         "CORRECT": "5 RL corrected by a safety controller", "EMBED": "6 RL embedded in optimisation layer"}


# Preprints whose peer-reviewed version has appeared (verified 2026-10-16 on Crossref or the proceedings site;
# stageD/preprint_published_check.csv). The study is cited in its published version; year kept as recorded.
PUBLISHED_VERSION = {
    "B0048": ("Proceedings of the AAAI Conference on Artificial Intelligence", "10.1609/aaai.v33i01.33013387"),
    "B0929": ("IEEE International Conference on Intelligent Transportation Systems (ITSC)", "10.1109/itsc60802.2025.11423819"),
    "B0944": ("IEEE Intelligent Vehicles Symposium (IV)", "10.1109/iv66570.2026.11623996"),
    "B1285": ("Proceedings of the 38th International Conference on Machine Learning (ICML), PMLR 139", ""),
    "B1639": ("IEEE International Conference on Robotics and Automation (ICRA)", "10.1109/icra57385.2026.11697389"),
    "B1692": ("IEEE International Conference on Robotics and Automation (ICRA)", "10.1109/icra57385.2026.11696348"),
    "C0083": ("Proceedings of the Conference on Robot Learning (CoRL), PMLR 100", ""),
}


# venues missing from the bibliographic metadata, taken from the proceedings DOI prefix (container-title verified on Crossref 2026-10-08)
VENUE_FROM_DOI = {
    # second update search (2026-11-13), proceedings names as printed on the papers' first pages
    "E035": "IEEE/CVF Conference on Computer Vision and Pattern Recognition, Findings Track (CVPRF)",
    # citation-search studies, Crossref container-title verified 2026-10-10 (scripts/22_doi_audit.py cache)
    "C0068": "International Joint Conference on Neural Networks (IJCNN)",                 # 10.1109/ijcnn.2019
    "C0130": "Robotics: Science and Systems (RSS)",                                       # 10.15607/rss.2020
    "C0173": "International Conference on Software Engineering & Computer Systems and International Conference on Computational Science and Information Management (ICSECS-ICOCSIM)",
    "C0219": "Emerging Technology in Computing, Communication and Electronics (ETCCE)",
    "C0552": "International Conference on Intelligent Driving and Smart Transportation",   # ACM 10.1145/3704657
    "C0566": "IEEE Cyber Science and Technology Congress (CyberSciTech)",
    "C0570": "Annual Computer Security Applications Conference Workshops (ACSAC Workshops)",
    "C0709": "International Conference on Automation in Manufacturing, Transportation and Logistics (ICaMaL)",
    "C0764": "International Conference on Computer Network and Cloud Computing",          # ACM 10.1145/3744451
    "C0914": "International Conference on Information, Communication and Automation Technologies (ICAT)",
    "C1022": "IIEEJ International Conference on Image Electronics and Visual Computing (IEVC)",
    "C1037": "International Conference on Robotics, Automation and Intelligent Transportation Systems (RAITS)",
    "C1048": "IEEE International Conference on Communications, Information System and Computer Engineering (CISCE)",
    "B0775": "International Conference on Computer Science and Artificial Intelligence (CSAI)",  # Crossref 10.1145/3788149.3788199
    "B1417": "International Symposium on Intelligent Unmanned Systems and Artificial Intelligence (SIUSAI)",  # Crossref 10.1145/3669721.3669735
    "B0160": "IEEE International Intelligent Transportation Systems Conference (ITSC)",  # 10.1109/itsc48978.2021
    "B1269": "IEEE International Intelligent Transportation Systems Conference (ITSC)",  # 10.1109/itsc48978.2021
    "B0738": "IEEE International Conference on Industrial Automation, Robotics and Control Engineering (IARCE)",  # 10.1109/iarce68366.2025
    "B1237": "IEEE/ACM International Conference on Computer-Aided Design (ICCAD)",        # 10.1145/3400302
    "B1479": "Robotics: Science and Systems (RSS)",                                       # 10.15607/rss.2024
    # batches 11-19, Crossref container-title verified 2026-10-08
    "B0629": "International Conference on Control Theory and Applications (ICoCTA)",       # 10.1109/icocta64736.2024
    "B0671": "IEEE International Conference on Software Quality, Reliability and Security (QRS)",  # 10.1109/qrs65678.2025
    "B0763": "International Conference on Data, Energy and Communication Networks (DECoN)",  # 10.1109/decon67170.2025
    "B0870": "International Conference on Mechatronics, Automation and Intelligent Control (MAIC)",  # 10.1109/maic67965.2025
    "B1162": "IEEE International Conference on Mechatronic and Embedded Systems and Applications (MESA)",  # 10.1109/mesa70578.2026
    "B1271": "IEEE International Intelligent Transportation Systems Conference (ITSC)",  # 10.1109/itsc48978.2021
    "B1277": "IEEE International Intelligent Transportation Systems Conference (ITSC)",  # 10.1109/itsc48978.2021
    "B1287": "IEEE International Intelligent Transportation Systems Conference (ITSC)",  # 10.1109/itsc48978.2021
    "B1470": "International Conference on Cloud Computing, Data Science and Engineering (Confluence)",  # 10.1109/confluence60223.2024
    "B1635": "Optical Communication, Photonics, Telecommunications, and Intelligent Machine Applications (OPTIMA)",  # 10.1109/optima67660.2025
}


def parse(path):
    recs, cur = [], None
    for ln, line in enumerate(open(path), 1):
        line = line.rstrip("\n")
        if line.startswith("#") or not line.strip():
            continue
        if line.startswith("@@ "):
            cur = {"study_id": line[3:].strip(), "_src": f"{path.name}:{ln}"}
            recs.append(cur)
            continue
        m = re.match(r"(\w+):\s?(.*)$", line)
        if not m or cur is None:
            raise SystemExit(f"{path.name}:{ln}: cannot parse line: {line[:80]}")
        cur[m.group(1)] = m.group(2).strip()
    return recs


def check(r):
    errs = []
    for f in FIELDS:
        if f not in r or r[f] == "":
            errs.append(f"missing {f}")
    for f in set(r) - set(FIELDS) - {"study_id", "_src"}:
        errs.append(f"unknown field {f}")
    for f, vocab in V.items():
        if f not in r:
            continue
        vals = [v.strip() for v in r[f].split(";")]
        if f in SINGLE and len(vals) > 1:
            errs.append(f"{f} must be single-valued")
        for v in vals:
            if v not in vocab and not v.startswith("OTHER:"):
                errs.append(f"{f}: '{v}' not in vocabulary")
    q = r.get("qa", "").split()
    if len(q) != 12 or any(x not in "012" for x in q):
        errs.append("qa must be 12 scores of 0/1/2")
    else:
        low = [i + 1 for i, x in enumerate(q) if x != "2"]
        note = r.get("qa_note", "")
        for i in low:
            if not re.search(rf"\bQ{i}\b", note):
                errs.append(f"qa_note lacks justification for Q{i}")
        for i in re.findall(r"\bQ(\d+)\b", note):
            if int(i) not in low:
                errs.append(f"qa_note justifies Q{i} but Q{i} scored 2")
    if r.get("mech_primary") and r.get("mech") and r["mech_primary"] not in r["mech"].split("; "):
        errs.append("mech_primary not among mech")
    return errs


def main():
    A = {r["study_id"]: r for r in csv.DictReader(open(W / "stageA" / "stageA_inventory.csv"))}
    B = {r["study_id"]: r for r in csv.DictReader(open(W / "stageB" / "records_unique.csv"))}
    B.update({r["study_id"]: r for r in csv.DictReader(open(W / "stageC" / "records.csv"))})
    if (W / "stageE" / "records.csv").exists():                 # second update search (2026-11-13)
        B.update({r["study_id"]: r for r in csv.DictReader(open(W / "stageE" / "records.csv"))})
    inc = [l.strip() for l in open(W / "fulltext" / "included_studies.txt") if l.strip()]
    links = {}
    for r in csv.DictReader(open(W / "fulltext" / "fulltext_decisions.csv")):
        if r["ft_decision"] == "Additional report":
            links.setdefault(r["linked_to"], []).append(r["study_id"])
    recs, problems = {}, []
    for p in sorted((X / "raw").glob("batch*.txt")):
        for r in parse(p):
            sid = r["study_id"]
            if sid not in inc:
                problems.append(f"{r['_src']} {sid}: not an included study")
            if sid in recs:
                problems.append(f"{r['_src']} {sid}: duplicate record")
            problems += [f"{r['_src']} {sid}: {e}" for e in check(r)]
            recs[sid] = r
    rows = []
    for sid in inc:
        if sid not in recs:
            continue
        r = recs[sid]
        m = A.get(sid) or B[sid]
        venue, doi, mtype = m["venue"].strip(), m.get("doi", ""), m.get("type", "")
        venue = venue or VENUE_FROM_DOI.get(sid, "")
        if sid in PUBLISHED_VERSION:
            venue, doi = PUBLISHED_VERSION[sid][0], PUBLISHED_VERSION[sid][1]   # PMLR papers have no DOI
        # publication type: venue text first, then metadata type, DOI prefix of proceedings, arXiv id
        conf_doi = re.search(r"10\.1109/(itsc|iv|icra|iros|cdc|acc|iarce)|10\.1145/3400302|10\.15607/rss", doi, re.I)
        if re.search(r"arxiv|preprint|ssrn|techrxiv", venue + doi, re.I):
            ptype = "preprint"
        elif re.search(r"conference|proceedings|symposium|workshop|lecture notes|EPTCS|IFAC-PapersOnLine|Applied and Computational Engineering|\bICRA\b|\bIROS\b|\bITSC\b|\bIV\b|\bCDC\b|\bACC\b",
                       venue, re.I):
            ptype = "conference"
        elif re.search(r"journal|transactions|IEEE Access|letters|magazine|research part|reports|sensors|machines|actuators|"
                       r"electronics|applied sciences|engineering|informatics|innovation", venue, re.I):
            ptype = "journal"
        elif mtype == "conference-paper" or conf_doi:
            ptype = "conference"
        elif mtype == "preprint" or (not venue and m.get("arxiv")):
            ptype, venue = "preprint", venue or "arXiv"
        else:
            ptype = "journal" if venue else "NR"
        q = [int(x) for x in r["qa"].split()]
        tot = sum(q)
        roles = [ROLE.get(r["rl_output"], "")]
        if r["safety_integration"] in INTEG:
            roles.append(INTEG[r["safety_integration"]])
        row = {"study_id": sid, "title": m["title"], "authors": m["authors"], "year": m["year"], "venue": venue,
               "doi": doi if sid in PUBLISHED_VERSION else m.get("doi", ""),
               "pub_type": "conference" if sid in PUBLISHED_VERSION else ptype, "linked_reports": ";".join(links.get(sid, [])) or "NA"}
        row.update({f: r[f] for f in FIELDS if f not in ("qa",)})
        row.update({f"Q{i+1}": q[i] for i in range(12)})
        row.update({"qa_total": tot, "qa_band": "High" if tot >= 18 else "Medium" if tot >= 12 else "Low",
                    "rl_role_s17": " | ".join(x for x in roles if x)})
        rows.append(row)
    if problems:
        print("VALIDATION PROBLEMS:")
        print("\n".join(problems))
    cols = list(rows[0]) if rows else []
    with open(X / "evidence_db.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    wb = Workbook(); ws = wb.active; ws.title = "Evidence"
    ws.append(cols)
    for r in rows:
        ws.append([ILLEGAL_CHARACTERS_RE.sub("", str(r[c])) for c in cols])
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.freeze_panes = "B2"
    qa = wb.create_sheet("QA")
    qcols = ["study_id", "year"] + [f"Q{i}" for i in range(1, 13)] + ["qa_total", "qa_band", "qa_note"]
    qa.append(qcols)
    for r in rows:
        qa.append([r[c] for c in qcols])
    for c in qa[1]:
        c.font = Font(bold=True)
    st = wb.create_sheet("Status")
    st.append(["included studies", len(inc)]); st.append(["extracted", len(rows)])
    st.append(["validation problems", len(problems)])
    wb.save(X / "evidence_db.xlsx")
    bands = {}
    for r in rows:
        bands[r["qa_band"]] = bands.get(r["qa_band"], 0) + 1
    print(f"extracted {len(rows)} of {len(inc)} included studies; QA bands {bands}; problems {len(problems)}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
