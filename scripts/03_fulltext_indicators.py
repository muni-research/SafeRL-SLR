"""Stage A step 3: full-text keyword indicators (screening aid only; decisions are made by reading).
Counts mentions of AV / driving-simulator terms in each PDF body (references section excluded where detectable).
Output: stageA/fulltext_indicators.csv
"""
import csv, json, re
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent.parent / "stageA"
TERMS = {
    "av": r"autonomous (?:vehicle|driving|car)s?|self-driving|automated (?:vehicle|driving)|connected (?:and )?(?:automated|autonomous) vehicle|intelligent vehicle",
    "driving_task": r"lane[- ]chang|lane[- ]keep|on-ramp|merging|intersection|overtak|adaptive cruise|car[- ]following|platoon|highway",
    "carla": r"\bCARLA\b", "sumo": r"\bSUMO\b", "highway_env": r"highway[- ]env", "metadrive": r"MetaDrive",
    "uav": r"\bUAVs?\b|quadrotor|drone", "robot_arm": r"manipulator|robot arm|grasp",
    "safety_gym": r"Safety[- ]?Gym(?:nasium)?|Bullet[- ]?Safety|OmniSafe|Safety[- ]?Gymnasium",
}
def main():
    rows = []
    for r in json.loads((OUT / "raw_extract.json").read_text()):
        doc = pymupdf.open(ROOT / r["rel_path"])
        txt = "".join(p.get_text() for p in doc)
        cut = max(txt.rfind("\nReferences\n"), txt.rfind("\nREFERENCES\n"), txt.rfind("\nBibliography\n"))
        body = txt[:cut] if cut > len(txt) * 0.4 else txt
        row = {"study_id": r["study_id"]}
        for k, pat in TERMS.items():
            row[k] = len(re.findall(pat, body, flags=0 if k in ("carla", "sumo", "metadrive") else re.I))
        rows.append(row)
    with open(OUT / "fulltext_indicators.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(len(rows), "rows")
if __name__ == "__main__":
    main()
