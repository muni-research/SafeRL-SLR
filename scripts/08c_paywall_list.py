"""Build fulltext/paywalled_articles.xlsx: records needing institutional access, grouped by publisher,
with clickable DOI links and the exact file name to save each PDF as. Include before Unsure."""
import os
MAIL = os.environ.get("SLR_CONTACT_EMAIL", "")  # optional polite-pool contact; never hard-coded
import csv, json, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

FT = Path(__file__).resolve().parent.parent / "fulltext"
B = FT.parent / "stageB"
dec = {r["study_id"]: r["decision"] for r in csv.DictReader(open(B / "screening_decisions.csv"))}
need = list(csv.DictReader(open(FT / "needs_institutional_access.csv")))
PFX = {"10.1109": "IEEE", "10.1016": "Elsevier (ScienceDirect)", "10.1007": "Springer", "10.3390": "MDPI",
       "10.1177": "SAGE", "10.1080": "Taylor & Francis", "10.1002": "Wiley", "10.1111": "Wiley", "10.1049": "IET (Wiley)",
       "10.1145": "ACM", "10.4271": "SAE International", "10.1155": "Hindawi (Wiley)", "10.1038": "Nature",
       "10.1061": "ASCE", "10.1177/03611981": "SAGE (TRB)", "10.3233": "IOS Press", "10.1142": "World Scientific",
       "10.1088": "IOP", "10.2139": "SSRN", "10.1117": "SPIE", "10.1115": "ASME", "10.23919": "IEEE (EUCA/IFAC)",
       "10.1609": "AAAI", "10.24963": "IJCAI", "10.1093": "Oxford UP", "10.1017": "Cambridge UP",
       "10.3389": "Frontiers", "10.1371": "PLOS", "10.5555": "ACM/other", "10.1360": "Science China"}
def publisher(doi):
    if not doi:
        return "No DOI (search by title)"
    for k in sorted(PFX, key=len, reverse=True):
        if doi.startswith(k):
            return PFX[k]
    return "Other (" + doi.split("/")[0] + ")"
def oa_status(doi):
    """OpenAlex open_access.is_oa: free to read somewhere (site may still block scripted downloads)."""
    if not doi:
        return "Unknown"
    u = f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}" + (f"?mailto={MAIL}" if MAIL else "")
    for i in range(4):
        try:
            d = json.load(urllib.request.urlopen(u, timeout=30))
            return "Free (open access) - download in browser" if d["open_access"]["is_oa"] else "Subscription"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "Unknown"
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return "Unknown"
with ThreadPoolExecutor(3) as ex:
    access = list(ex.map(lambda r: oa_status(r["doi"]), need))
for r, a in zip(need, access):
    r["publisher"] = publisher(r["doi"]); r["screening"] = dec.get(r["study_id"], ""); r["access"] = a
need.sort(key=lambda r: (r["publisher"], r["screening"] != "Include", r["study_id"]))
wb = Workbook(); ws = wb.active; ws.title = "Paywalled"
hdr = ["#", "Study ID", "Priority", "Access", "Publisher", "Year", "Title", "Venue", "DOI link", "Save PDF as", "Done?"]
ws.append(hdr)
for c in ws[1]:
    c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="2F4F6F")
for i, r in enumerate(need, 1):
    ws.append([i, r["study_id"], "High (Include)" if r["screening"] == "Include" else "Normal (Unsure)",
               r["access"], r["publisher"], r["year"], r["title"], r["venue"], r["link"], f"{r['study_id']}.pdf", ""])
    cell = ws.cell(ws.max_row, 9)
    if r["link"].startswith("http"):
        cell.hyperlink = r["link"]; cell.font = Font(color="0563C1", underline="single")
for col, w in zip("ABCDEFGHIJK", [5, 9, 15, 30, 22, 6, 70, 40, 38, 12, 7]):
    ws.column_dimensions[col].width = w
ws.freeze_panes = "C2"; ws.auto_filter.ref = ws.dimensions
s = wb.create_sheet("By publisher"); s.append(["Publisher", "Total", "Include", "Unsure"])
cnt = Counter(r["publisher"] for r in need); inc = Counter(r["publisher"] for r in need if r["screening"] == "Include")
for p, n in cnt.most_common():
    s.append([p, n, inc[p], n - inc[p]])
s.append(["TOTAL", len(need), sum(inc.values()), len(need) - sum(inc.values())])
s.append([]); s.append(["Access", "Total", "Include", "Unsure"])
ca = Counter(r["access"] for r in need); ia = Counter(r["access"] for r in need if r["screening"] == "Include")
for a, n in ca.most_common():
    s.append([a, n, ia[a], n - ia[a]])
s.column_dimensions["A"].width = 30
h = wb.create_sheet("How to"); 
for line in ["1. Open each DOI link while on your institution's network/VPN and download the PDF.",
             "2. Save it into:  SLR_Workspace/fulltext/institutional/",
             "3. Name it exactly as in the 'Save PDF as' column (e.g. B0123.pdf).",
             "4. Priority 'High (Include)' papers matter most; 'Normal (Unsure)' ones may be excluded at full text.",
             "5. Papers you cannot obtain are reported in PRISMA as 'reports not retrieved' (no need to force it).",
             "6. Tell Claude when done; re-running scripts/08_fetch_fulltext.py detects the new files."]:
    h.append([line])
h.column_dimensions["A"].width = 110
wb.save(FT / "paywalled_articles.xlsx")
print(dict(Counter(r["access"] for r in need)))
print(len(need), "not retrieved;", dict(cnt.most_common()), "| Include:", sum(inc.values()))
