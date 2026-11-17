#!/usr/bin/env python3
"""Phase 6 figures (CLAUDE.md §29). Every number is computed here from extraction/evidence_db.csv
(via srl_common) or from manuscript/generated/prisma_counts.json; nothing is typed by hand.

Output: manuscript/figures/figNN_<name>.pdf (vector, used by LaTeX) and .png (300 dpi preview).
Usage:  python3 scripts/18_figures.py
"""
import csv
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Patch
from matplotlib.lines import Line2D
import numpy as np

import srl_common as S

OUT = S.W / "manuscript" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
R, N = S.R, S.N

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5, "legend.fontsize": 6.3, "axes.linewidth": 0.6, "pdf.fonttype": 42,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
})
FULL, HALF = 5.15, 2.55                        # inches; = \textwidth of the sn-jnl layout (372 pt), so fonts print at size
# Okabe-Ito (colour-blind safe) and an ordered ramp for the evidence levels
OI = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#000000"]
LEVEL_C = {"L0": "#efefef", "L1": "#c6dbef", "L2": "#9ecae1", "L3": "#4292c6", "L4": "#08519c",
           "L5": "#08306b"}
CLUSTER_C = dict(zip(S.CLUSTERS, ["#E69F00", "#0072B2", "#009E73", "#CC79A7", "#D55E00", "#56B4E9"]))
SHORT = {c: c.split(" ", 1)[1] for c in S.CLUSTERS}
WRAP = {"M1 Objective shaping": "Objective shaping", "M2 Run-time intervention": "Run-time intervention",
        "M3 Control-theoretic certificates": "Control-theoretic\ncertificates", "M4 Formal methods": "Formal methods",
        "M5 Robustness and uncertainty": "Robustness and\nuncertainty",
        "M6 Learning-paradigm extensions": "Learning-paradigm\nextensions"}
INK, GREY = "#222222", "#666666"


MIN_PT = 6.0          # smallest lettering at print size (Springer artwork guidance: 8-12 pt preferred, never below 6)


def save(fig, name, width=FULL):
    """Save at print size: no text below MIN_PT, and the trimmed figure no wider than its printed width, so that
    LaTeX does not shrink it (a shrunk figure would print its lettering below MIN_PT)."""
    import matplotlib.text as mtext
    fig.canvas.draw()                                    # tick labels exist only after a draw
    for ax_ in fig.axes:
        for axis in (ax_.xaxis, ax_.yaxis):
            old = [t.get_text() for t in axis.get_ticklabels()]
            new = [S.us_spelling(s) for s in old]
            if new != old:
                axis.set_ticks(axis.get_ticklocs()); axis.set_ticklabels(new)
    for t in fig.findobj(mtext.Text):
        if t.get_text().strip():
            t.set_text(S.us_spelling(t.get_text()))          # US spelling in all figure lettering
        if t.get_text().strip() and t.get_fontsize() < MIN_PT:
            t.set_fontsize(MIN_PT)
    for _ in range(6):
        fig.canvas.draw()
        bb = fig.get_tightbbox(fig.canvas.get_renderer())
        w = bb.width + 2 * plt.rcParams["savefig.pad_inches"]
        if w <= width * 1.005:
            break
        fw, fh = fig.get_size_inches()
        fig.set_size_inches(fw * width / w, fh)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=300)
    plt.close(fig)
    print("wrote", name)


def box(ax, x, y, w, h, text, fc="white", ec=INK, fs=7, lw=0.7, weight="normal", ha="center",
        color=INK, wrap=True):
    """Rounded box with text; lines are wrapped to the box width (axes coordinates on a full-figure axis)."""
    import textwrap
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.008",
                                fc=fc, ec=ec, lw=lw))
    if wrap:
        import re as _re                      # keep 'n = 123' and 'label: 123' on one line
        text = _re.sub(r"\bn = ", "n\u00a0=\u00a0", text)
        text = _re.sub(r": (\d)", ":\u00a0\\1", text)
        fig_w = ax.figure.get_size_inches()[0]
        chars = max(8, int((w - 0.016) * fig_w * 72 / (fs * 0.54)))
        lines = []
        for ln in text.split("\n"):
            ind = len(ln) - len(ln.lstrip(" "))
            lines += textwrap.wrap(ln, width=chars, subsequent_indent=" " * (ind + 2), initial_indent="") or [""]
        text = "\n".join(lines)
    tx = x + w / 2 if ha == "center" else x + 0.008
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fs, weight=weight, color=color,
            linespacing=1.2)


def arrow(ax, x0, y0, x1, y1, lw=0.7, color=INK):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", lw=lw, color=color, shrinkA=0, shrinkB=0,
                                mutation_scale=7))


# ------------------------------------------------------------------------------------------------
# Figure 1: PRISMA 2020 flow diagram
def fig_prisma():
    """PRISMA 2020 flow diagram (new reviews with searches of databases, registers and other methods).
    Laid out in inches: every box is sized to its wrapped text, so there is no empty space inside boxes, and every
    arrow runs exactly from one box edge to the next."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch as FB
    from matplotlib.font_manager import FontProperties
    P = S.PRISMA
    idf, scr, el, om = P["identification"], P["screening"], P["eligibility"], P.get("other_methods") or {}
    inc = P["included"]
    W = FULL
    fs, fsh, fsb = 6.4, 7.0, 7.0                       # body, column headers, phase labels
    PADX, PADY, LS = 0.055, 0.05, 1.22                  # inner padding (in) and line spacing
    BAND, G0 = 0.20, 0.06                               # phase band width, gap band -> first box
    MW, SW, GH, GC = 1.00, 1.20, 0.13, 0.15             # main/side widths, gap main->side, gap between columns
    xA = BAND + G0; xB = xA + MW + GH; xC = xB + SW + GC; xD = xC + MW + GH
    W_used = xD + SW
    fig = plt.figure(figsize=(W, 9))
    rend = fig.canvas.get_renderer()

    def tw(s, size, weight="normal"):
        w, h, d = rend.get_text_width_height_descent(s, FontProperties(family=plt.rcParams["font.sans-serif"], size=size, weight=weight), ismath=False)
        return w / fig.dpi

    def wrap(text, width, size, weight="normal"):
        out = []
        for ln in text.split("\n"):
            ind = len(ln) - len(ln.lstrip(" ")); words = [w for w in ln.split(" ") if w]; cur = " " * ind
            for wd in words:
                cand = (cur + " " + wd) if cur.strip() else cur + wd
                if tw(cand, size, weight) <= width or not cur.strip():
                    cur = cand
                else:
                    out.append(cur); cur = " " * (ind + 2) + wd
            out.append(cur)
        return "\n".join(out)

    def height(text, size):
        return (text.count("\n") + 1) * size * LS / 72 + 2 * PADY - size * (LS - 1) / 72

    nb = lambda s: s.replace("n = ", "n = ")
    lab = {"EC1": "non-road domain", "EC2": "not RL", "EC3": "safety superficial", "EC4": "non-research item",
           "EC5": "duplicate report", "EC6": "insufficient detail", "EC8": "thesis", "EC9": "review or survey",
           "EC10": "RL used to test AVs", "EC11": "not in English"}
    def reasons(rr):
        return "\n".join(f"  {lab[k]}: {rr[k]}" for k in sorted(rr, key=lambda k: -rr[k]))
    db = idf["records_by_database"]; d = idf["duplicates_detail"]
    names = {"SemanticScholar": "Semantic Scholar"}
    T = {  # (main text, side text) per row and column
        ("id", 0): (f"Records identified (n = {idf['records_supplied_corpus'] + idf['records_databases_total']})\n"
                    f"Seed corpus (n = {idf['records_supplied_corpus']})\nDatabases (n = {idf['records_databases_total']}):\n"
                    + "\n".join(f"{names.get(k, k)} {v}" for k, v in sorted(db.items(), key=lambda kv: -kv[1])),
                    f"Records removed before screening:\nDuplicates (n = {idf['duplicates_removed_total']})\n"
                    f"  within seed corpus: {d['within_supplied_corpus']}\n  across databases: {d['within_database_results']}\n"
                    f"  already in seed corpus: {d['database_records_already_in_supplied_corpus']}\n"
                    f"  found at screening: {d['found_manually_at_screening']}"),
        ("id", 1): (f"Records identified (n = {om['records_identified']})\nBackward citations (n = {om['backward']})\n"
                    f"Forward citations (n = {om['forward']})\nUpdate searches (n = {om['update_search']} and {om.get('update_search_2', 0)})",
                    f"Records removed before screening:\nDuplicates (n = {om['duplicates_removed']}; "
                    f"{om['duplicates_already_screened']} already screened)\nMarked ineligible by automation tool "
                    f"(keyword filter, n = {om['removed_by_automation_keyword_filter']})"),
        ("scr", 0): (f"Records screened\n(n = {scr['records_screened']})",
                     f"Records excluded (n = {scr['records_excluded']})\nincl. {scr['of_which_background_pool_EC1']} to background pool\n"
                     f"{reasons(scr['excluded_by_reason'])}"),
        ("scr", 1): (f"Records screened\n(n = {om['records_screened']})",
                     f"Records excluded (n = {om['records_excluded'] + om['duplicates_found_at_screening']})\n"
                     f"incl. {om['of_which_background_pool_EC1']} to background pool and {om['duplicates_found_at_screening']} "
                     f"duplicates found at screening\n{reasons(om['screening_excluded_by_reason'])}"),
        ("ret", 0): (f"Reports sought for retrieval\n(n = {el['reports_sought_for_retrieval']})",
                     f"Reports not retrieved\n(n = {el['not_retrieved']})"),
        ("ret", 1): (f"Reports sought for retrieval\n(n = {om['reports_sought']})", f"Reports not retrieved\n(n = {om['not_retrieved']})"),
        ("ass", 0): (f"Reports assessed for eligibility\n(n = {el['fulltext_assessed']})",
                     f"Reports excluded (n = {el['fulltext_excluded']})\n{reasons(el['fulltext_excluded_by_reason'])}"),
        ("ass", 1): (f"Reports assessed for eligibility\n(n = {om['assessed']})",
                     f"Reports excluded (n = {om['excluded']})\n{reasons(om['fulltext_excluded_by_reason'])}"),
    }
    T = {k: (wrap(nb(m), MW - 2 * PADX, fs), wrap(nb(s), SW - 2 * PADX, fs)) for k, (m, s) in T.items()}
    rows = ["id", "scr", "ret", "ass"]
    VG = 0.20                                            # vertical gap between rows (arrow length)
    HEAD = 0.30                                          # header bars
    y = 0.0; geo = {}
    y -= HEAD + 0.10
    for r in rows:
        mh = max(height(T[(r, c)][0], fs) for c in (0, 1)); sh = max(height(T[(r, c)][1], fs) for c in (0, 1))
        rh = max(mh, sh); geo[r] = (y, rh, mh, sh); y -= rh + VG
    t_bold = f"Studies included in review (n = {inc['studies']})\nReports of included studies (n = {inc['reports']})"
    t_body = (f"Databases and seed corpus: {inc.get('studies_databases')} studies "
              f"({el['fulltext_assessed'] - el['fulltext_excluded']} reports); citation and update searches: "
              f"{inc.get('studies_other_methods')} studies ({om['assessed'] - om['excluded']} reports).\n"
              f"Reports include linked conference, journal and preprint versions of the same study. "
              f"All {inc['studies']} studies enter the qualitative and descriptive quantitative synthesis.")
    IX0, IX1 = xA, xD + SW
    t_body = wrap(nb(t_body), IX1 - IX0 - 2 * PADX, fs)
    hb = (t_bold.count("\n") + 1) * 7.0 * LS / 72; hbody = height(t_body, fs) - 2 * PADY
    ih = hb + 0.04 + hbody + 2 * PADY
    yinc = y; ybot = yinc - ih
    H = -ybot + 0.02
    fig.set_size_inches(W, H)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(-H, 0); ax.axis("off")

    def rect(x, top, w, h, fc="white", ec=INK, lw=0.75):
        ax.add_patch(FB((x, top - h), w, h, boxstyle="round,pad=0,rounding_size=0.035", fc=fc, ec=ec, lw=lw))

    def put(x, top, w, h, text, ha):
        tx = x + w / 2 if ha == "center" else x + PADX
        ax.text(tx, top - h / 2, text, ha=ha, va="center", fontsize=fs, color=INK, linespacing=LS, multialignment=ha)

    def arr(x0, y0, x1, y1):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>,head_length=0.55,head_width=0.3",
                                     mutation_scale=9, lw=0.9, color=INK, shrinkA=0, shrinkB=0.4))

    # header bars and phase bands
    for x0, x1, txt, col in [(xA, xB + SW, "Databases and seed corpus", "#fdd49e"),
                             (xC, xD + SW, "Other methods (citation and update searches)", "#d9d9d9")]:
        ax.add_patch(FB((x0, -HEAD), x1 - x0, HEAD - 0.02, boxstyle="round,pad=0,rounding_size=0.035", fc=col, ec="none"))
        ax.text((x0 + x1) / 2, -HEAD / 2 - 0.01, txt, ha="center", va="center", fontsize=fsh, weight="bold")
    bands = [("Identification", geo["id"][0], geo["id"][0] - geo["id"][1]),
             ("Screening", geo["scr"][0], geo["ass"][0] - geo["ass"][1]),
             ("Included", yinc, ybot)]
    for name, t, b in bands:
        ax.add_patch(FB((0.01, b), BAND - 0.02, t - b, boxstyle="round,pad=0,rounding_size=0.035", fc="#dbe9f6", ec="none"))
        ax.text(BAND / 2, (t + b) / 2, name, rotation=90, ha="center", va="center", fontsize=fsb, weight="bold", color="#08306b")
    # boxes and arrows
    for c, (xm, xs) in enumerate([(xA, xB), (xC, xD)]):
        prev_bottom = None
        for r in rows:
            top, rh, mh, sh = geo[r]
            mt = top - (rh - mh) / 2; st = top - (rh - sh) / 2       # centre main and side box in the row
            m, s = T[(r, c)]
            rect(xm, mt, MW, mh); put(xm, mt, MW, mh, m, "center")
            rect(xs, st, SW, sh); put(xs, st, SW, sh, s, "left")
            yc = top - rh / 2
            arr(xm + MW, yc, xs, yc)
            if prev_bottom is not None:
                arr(xm + MW / 2, prev_bottom, xm + MW / 2, mt)
            prev_bottom = mt - mh
        arr(xm + MW / 2, prev_bottom, xm + MW / 2, yinc)
    rect(IX0, yinc, IX1 - IX0, ih, fc="#eef4fb")
    ax.text((IX0 + IX1) / 2, yinc - PADY, nb(t_bold), ha="center", va="top", fontsize=7.0, weight="bold",
            linespacing=LS, color=INK)
    ax.text((IX0 + IX1) / 2, yinc - PADY - hb - 0.04, t_body, ha="center", va="top", fontsize=fs,
            linespacing=LS, color=INK)
    save(fig, "fig01_prisma")


# ------------------------------------------------------------------------------------------------
# Figure 2: two-layer taxonomy (clusters -> mechanisms) with study counts and share at L3+
def fig_taxonomy():
    fig = plt.figure(figsize=(FULL, 7.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    box(ax, 0.25, 0.925, 0.50, 0.06, f"Safe RL for autonomous vehicles: {N} included studies",
        fc="#08306b", ec="#08306b", color="white", weight="bold", fs=7.5)
    cw, gx = 0.31, 0.02
    x0 = (1 - (3 * cw + 2 * gx)) / 2
    tops = [0.875, 0.505]
    mh, mg = 0.042, 0.006
    for i, c in enumerate(S.CLUSTERS):
        row, col = divmod(i, 3)
        x = x0 + col * (cw + gx); ytop = tops[row]
        rs = [r for r in R if c in r["_clusters"]]
        clr = CLUSTER_C[c]
        box(ax, x, ytop - 0.065, cw, 0.065,
            f"{c}\n{len(rs)} studies ({S.pct(len(rs), N)}%); L3+ {S.pct(sum(map(S.l3plus, rs)), len(rs))}%",
            fc=clr, ec=clr, color="white", weight="bold", fs=6.5)
        y = ytop - 0.065 - 0.012
        for m in S.CLUSTER_MECHS[c]:
            ms = [r for r in R if S.has(r, m)]
            txt = f"{m}  {S.MECH[m]}: n = {len(ms)}" + (f"; L3+ {S.pct(sum(map(S.l3plus, ms)), len(ms)):.0f}%" if ms else " (not observed)")
            box(ax, x, y - mh, cw, mh, txt, fc="white", ec=clr, fs=6, lw=0.8)
            y -= mh + mg
    ax.text(0.5, 0.012, "Counts are studies (a study can use several mechanisms). L3+: share of studies whose highest "
            "substantiated evidence level is run-time enforcement (L3) or stronger.", ha="center", fontsize=6, color=GREY,
            wrap=True)
    save(fig, "fig02_taxonomy")


# ------------------------------------------------------------------------------------------------
# Figure 3: how the learned policy is coupled to safety (RL output -> run-time safety attachment)
def fig_architecture():
    outs = [("ACT", "Control action"), ("DEC", "High-level decision"), ("TRAJ", "Trajectory / path"),
            ("PARAM", "Controller parameters"), ("RES", "Residual on MPC/expert")]
    ints = [("FILTER", "Safety filter / projection"), ("MASK", "Action mask / shield"),
            ("CORRECT", "Corrective or fallback\ncontroller"), ("EMBED", "Embedded in an optimisation\nor control law"),
            ("NONE", "No separate run-time\nsafety component")]
    ct = Counter((r["rl_output"], r["safety_integration"]) for r in R)
    lo = {o: sum(ct[(o, i)] for i, _ in ints) for o, _ in outs}
    ri = {i: sum(ct[(o, i)] for o, _ in outs) for i, _ in ints}
    fig = plt.figure(figsize=(FULL, 4.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    # pipeline header
    stages = [("Perceived state\n(vector 92%, image/BEV/LiDAR rare)", "#f0f0f0"), ("RL policy", "#dbe9f6"),
              ("RL output", "#dbe9f6"), ("Run-time safety layer", "#d9f0d3"), ("Vehicle / low-level\ncontrol", "#f0f0f0")]
    vec = S.pct(sum("VEC" in S.split(r["obs_type"]) for r in R), N)
    stages[0] = (f"Perceived state\n(state vectors {vec}%)", "#f0f0f0")
    xs = [0.01, 0.208, 0.406, 0.604, 0.802]
    for (t, c), x in zip(stages, xs):
        box(ax, x, 0.86, 0.18, 0.11, t, fc=c, ec=GREY, fs=6.2, weight="bold")
    for a, b in zip(xs[:-1], xs[1:]):
        arrow(ax, a + 0.18, 0.915, b, 0.915)
    tr = sum(r["mech_stage"] == "TRAIN" for r in R)
    ax.annotate("", xy=(0.30, 0.875), xytext=(0.69, 0.875),
                arrowprops=dict(arrowstyle="-|>", lw=0.6, ls="--", color=GREY,
                                connectionstyle="arc3,rad=-0.18", mutation_scale=7))
    ax.text(0.495, 0.79, f"training-time safety (reward, cost, constraint, critic) is the only mechanism stage in "
            f"{tr} studies ({S.pct(tr, N)}%)", ha="center", fontsize=6, color=GREY)
    # alluvial between outputs (left) and integrations (right)
    top, bottom, gapn = 0.72, 0.02, 0.022
    scale = (top - bottom - gapn * 4) / N
    xl, xr, nw = 0.16, 0.66, 0.035
    lpos, y, last = {}, top, 1.0
    for o, lab in outs:
        h = lo[o] * scale; lpos[o] = [y, y - h]
        ax.add_patch(plt.Rectangle((xl, y - h), nw, h, fc="#0072B2", ec="none"))
        ly = min(y - h / 2, last - 0.075); last = ly
        ax.text(xl - 0.008, ly, f"{lab.replace(chr(10), ' ')}: {lo[o]} ({S.pct(lo[o], N)}%)", ha="right",
                va="center", fontsize=6.3)
        y -= h + gapn
    rpos, y = {}, top
    icol = {"FILTER": "#009E73", "MASK": "#56B4E9", "CORRECT": "#E69F00", "EMBED": "#CC79A7", "NONE": "#bdbdbd"}
    for i, lab in ints:
        h = ri[i] * scale; rpos[i] = [y, y - h]
        ax.add_patch(plt.Rectangle((xr, y - h), nw, h, fc=icol[i], ec="none"))
        ax.text(xr + nw + 0.008, y - h / 2, f"{lab}\n{ri[i]} ({S.pct(ri[i], N)}%)", ha="left", va="center", fontsize=6.3)
        y -= h + gapn
    for o, _ in outs:
        for i, _ in ints:
            n = ct[(o, i)]
            if not n:
                continue
            h = n * scale
            l0, l1 = lpos[o][0], lpos[o][0] - h; lpos[o][0] = l1
            r0, r1 = rpos[i][0], rpos[i][0] - h; rpos[i][0] = r1
            t = np.linspace(0, 1, 40); s = 3 * t ** 2 - 2 * t ** 3
            xa = xl + nw + (xr - xl - nw) * t
            upper = l0 + (r0 - l0) * s; lower = l1 + (r1 - l1) * s
            ax.add_patch(Polygon(np.r_[np.c_[xa, upper], np.c_[xa[::-1], lower[::-1]]],
                                 fc=icol[i], ec="none", alpha=0.45))
    save(fig, "fig03_integration")


# ------------------------------------------------------------------------------------------------
# Figure 4: safety-evidence profile of each mechanism (100% stacked by highest level)
def fig_mechanism_evidence():
    codes = [m for m in "ABCDEFGHIJKLNOPQRSTUVWX" if any(S.has(r, m) for r in R)]
    rows = []
    for m in codes:
        ms = [r for r in R if S.has(r, m)]
        c = Counter(r["safety_level"] for r in ms)
        rows.append((m, len(ms), [100 * c[l] / len(ms) for l in S.LEVELS], S.pct(sum(map(S.l3plus, ms)), len(ms))))
    rows.sort(key=lambda t: t[3])
    fig, ax = plt.subplots(figsize=(FULL, 4.8))
    yy = np.arange(len(rows))
    left = np.zeros(len(rows))
    for j, l in enumerate(S.LEVELS):
        v = np.array([r[2][j] for r in rows])
        ax.barh(yy, v, left=left, color=LEVEL_C[l], height=0.72, label=l, ec="white", lw=0.3)
        left += v
    ax.set_yticks(yy)
    ax.set_yticklabels([f"{m}  {S.MECH[m]}  (n = {n})" for m, n, _, _ in rows])
    for k, r in enumerate(rows):
        ax.text(101, k, f"{r[3]:.0f}%", va="center", fontsize=6.3, color=INK)
        col = CLUSTER_C[S.CLUSTER[r[0]]]
        ax.add_patch(plt.Rectangle((-1.6, k - 0.36), 1.2, 0.72, color=col, clip_on=False))
    ax.tick_params(axis="y", pad=7, length=0)
    ax.text(101, len(rows) - 0.2, "L3+", fontsize=6.5, weight="bold")
    ax.set_xlim(0, 100); ax.set_xlabel("Share of studies using the mechanism, by highest safety-evidence level (%)")
    ax.set_ylim(-0.6, len(rows) - 0.4)
    h1 = [Patch(color=LEVEL_C[l], label=l) for l in S.LEVELS]
    h2 = [Patch(color=CLUSTER_C[c], label=c) for c in S.CLUSTERS]
    ax.legend(handles=h1 + h2, ncol=4, loc="upper center", bbox_to_anchor=(0.32, -0.11), frameon=False,
              columnspacing=1.0, handlelength=1.2)
    save(fig, "fig04_mechanism_evidence")


# ------------------------------------------------------------------------------------------------
# Figure 5: evolution (a) studies per year by level, (b) feature shares per period
def fig_evolution():
    years = list(range(2016, 2027))
    fig, (a, b) = plt.subplots(2, 1, figsize=(FULL, 5.8), gridspec_kw={"height_ratios": [1, 1.1]})
    bottom = np.zeros(len(years))
    for l in S.LEVELS:
        v = np.array([sum(r["_year"] == y and r["safety_level"] == l for r in R) for y in years])
        a.bar(years, v, bottom=bottom, color=LEVEL_C[l], label=l, width=0.75, ec="white", lw=0.3)
        bottom += v
    for y, t in zip(years, bottom):
        a.text(y, t + 1.5, int(t), ha="center", fontsize=6)
    a.set_xticks(years); a.set_xticklabels([str(y)[2:] if y < 2026 else "26*" for y in years])
    a.set_ylabel("Included studies"); a.set_title("(a) Studies per year by highest evidence level", loc="left")
    a.legend(ncol=2, frameon=False, loc="upper left")
    a.text(0.0, -0.13, "*2026 partial year", transform=a.transAxes, fontsize=6, color=GREY)
    per = [p[0] for p in S.PERIODS]
    feats = [("Reward design (A)", lambda r: S.has(r, "A"), OI[0], "-"),
             ("Constrained RL (B)", lambda r: S.has(r, "B"), OI[1], "-"),
             ("CBF/CLF/QP (F,G,H)", lambda r: any(S.has(r, m) for m in "FGH"), OI[2], "-"),
             ("MPC hybrid (I)", lambda r: S.has(r, "I"), OI[6], "-"),
             ("Shield/filter/RTA (D,E,S)", lambda r: any(S.has(r, m) for m in "DES"), OI[4], "-"),
             ("Formal methods (T)", lambda r: S.has(r, "T"), OI[5], "-"),
             ("Robust/risk/uncertainty (K,L,N)", lambda r: any(S.has(r, m) for m in "KLMN"), OI[3], "-"),
             ("Multi-agent", lambda r: r["agents"] != "SA", OI[7], "-"),
             ("Evidence level L3+", S.l3plus, "#08306b", "--"),
             ("Physical / HIL validation", lambda r: r["_physical"], "#08306b", ":"),
             ("Code released", lambda r: r["code"] == "Y", GREY, "-.")]
    x = np.arange(len(per))
    markers = ["o", "s", "^", "D", "v", "P", "X", "*", "h", "<", ">"]   # shape as a second cue (greyscale, CVD)
    for (lab, f, col, ls), mk in zip(feats, markers):
        v = [S.pct(sum(f(r) for r in R if r["_period"] == p), sum(r["_period"] == p for r in R)) for p in per]
        b.plot(x, v, ls=ls, marker=mk, ms=3.2, lw=1.1, color=col, label=lab, markeredgewidth=0.4)
    nper = [sum(r["_period"] == p for r in R) for p in per]
    b.set_xticks(x); b.set_xticklabels([f"{p}\n(n = {n})" for p, n in zip(per, nper)])
    b.set_ylabel("Share of the period's studies (%)"); b.set_ylim(0, 70)
    b.set_title("(b) Methods and evidence by period", loc="left")
    b.legend(fontsize=6, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.02), handlelength=2.2)
    fig.tight_layout(w_pad=1.2)
    save(fig, "fig05_evolution")


# ------------------------------------------------------------------------------------------------
# Figure 6: application distribution by task and evidence level
def fig_applications():
    tasks = sorted(S.TASK, key=lambda t: sum(t in S.split(r["task"]) for r in R))
    fig, ax = plt.subplots(figsize=(FULL * 0.9, 3.6))
    yy = np.arange(len(tasks)); left = np.zeros(len(tasks))
    for l in S.LEVELS:
        v = np.array([sum(t in S.split(r["task"]) and r["safety_level"] == l for r in R) for t in tasks])
        ax.barh(yy, v, left=left, color=LEVEL_C[l], label=l, height=0.72, ec="white", lw=0.3)
        left += v
    for k, t in enumerate(tasks):
        ts = [r for r in R if t in S.split(r["task"])]
        ax.text(left[k] + 1.5, k, f"{len(ts)}  (L4+ {S.pct(sum(map(S.l4plus, ts)), len(ts)):.0f}%)",
                va="center", fontsize=6)
    ax.set_yticks(yy); ax.set_yticklabels([S.TASK[t] for t in tasks])
    ax.set_xlabel("Studies (a study can address several tasks)"); ax.set_xlim(0, max(left) * 1.3)
    ax.legend(ncol=6, frameon=False, loc="lower center", bbox_to_anchor=(0.4, -0.2), handlelength=1)
    save(fig, "fig06_applications", width=FULL * 0.9)


# ------------------------------------------------------------------------------------------------
# Figure 7: RL algorithm family x safety-mechanism cluster
def fig_alg_mech():
    fams = [f for f in S.FAMILIES if any(f in r["_fam"] for r in R)]
    M = np.array([[sum(f in r["_fam"] and c in r["_clusters"] for r in R) for c in S.CLUSTERS] for f in fams])
    nf = [sum(f in r["_fam"] for r in R) for f in fams]
    P = M / np.array(nf)[:, None] * 100
    fig, ax = plt.subplots(figsize=(FULL, 3.4))
    # vector cells (pcolormesh) instead of a raster image, so the figure stays resolution-independent
    im = ax.pcolormesh(np.arange(len(S.CLUSTERS) + 1) - 0.5, np.arange(len(fams) + 1) - 0.5, P, cmap="Blues",
                       vmin=0, vmax=100, shading="flat", rasterized=False)
    ax.set_xlim(-0.5, len(S.CLUSTERS) - 0.5); ax.set_ylim(len(fams) - 0.5, -0.5)
    for i in range(len(fams)):
        for j in range(len(S.CLUSTERS)):
            ax.text(j, i, f"{M[i, j]}\n({P[i, j]:.0f}%)", ha="center", va="center", fontsize=6,
                    color="white" if P[i, j] > 55 else INK)
    ax.set_xticks(range(len(S.CLUSTERS)))
    ax.set_xticklabels([c.split(" ")[0] + "\n" + "\n".join(w.replace("-", "-\n") for w in c.split(" ")[1:])
                        for c in S.CLUSTERS], fontsize=6, linespacing=1.0)
    ax.set_yticks(range(len(fams))); ax.set_yticklabels([f"{f} (n = {n})" for f, n in zip(fams, nf)])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cb.set_label("% of the family's studies", fontsize=6.5)
    cb.ax.tick_params(labelsize=6)
    cb.solids.set_rasterized(False)                # matplotlib rasterizes long colour bars by default
    save(fig, "fig07_algorithm_mechanism")


# ------------------------------------------------------------------------------------------------
# Figure 8: validation landscape (a) evidence level x validation tier, (b) simulators x tier
def fig_validation():
    tiers = [t for t in S.TIER if t != "DEPLOY"]
    tl = {"SIM-LOW": "Low-fid.\nsim.", "SIM-HIFI": "High-fid.\nsim.", "SIM-DATA": "Data-\ndriven",
          "HIL": "HIL", "SCALED": "Scaled\nvehicle", "CLOSED": "Closed\ncourse", "ROAD": "Public\nroad"}
    fig, (a, b) = plt.subplots(2, 1, figsize=(FULL, 6.6), gridspec_kw={"height_ratios": [1, 1]})
    for i, l in enumerate(S.LEVELS):
        for j, t in enumerate(tiers):
            n = sum(r["safety_level"] == l and r["validation_tier"] == t for r in R)
            if n:
                a.scatter(j, i, s=max(n * 9, 70), color=LEVEL_C[l], ec=INK, lw=0.3, zorder=3)
                a.text(j, i, n, ha="center", va="center", fontsize=6,
                       color="white" if l in ("L3", "L4", "L5") else INK, zorder=4)
    a.axvspan(2.5, 6.5, color="#fff2cc", zorder=0)
    a.text(4.5, 5.75, "physical / HIL", ha="center", fontsize=6, color="#8a6d00")
    a.set_xticks(range(len(tiers))); a.set_xticklabels([tl[t] for t in tiers], fontsize=6)
    a.set_yticks(range(6)); a.set_yticklabels(S.LEVELS); a.set_ylim(-0.6, 6.1); a.set_xlim(-0.6, 6.6)
    a.set_title("(a) Evidence level vs highest validation tier", loc="left")
    a.grid(color="#eeeeee", lw=0.5, zorder=0)
    sims = Counter(s for r in R for s in S.split(r["simulator"]) if not s.startswith("OTHER:") and s != "NR")
    top = [s for s, _ in sims.most_common(10)]
    nm = {"CUSTOM": "Custom", "HWENV": "highway-env", "METADRIVE": "MetaDrive", "SIMULINK": "MATLAB/Simulink", "UNITY": "Unity", "PRESCAN": "PreScan",
          "CARSIM": "CarSim", "SAFETYGYM": "Safety Gym", "PRESCAN": "PreScan", "COMMONROAD": "CommonRoad"}
    yy = np.arange(len(top))[::-1]; left = np.zeros(len(top))
    tcol = {"SIM-LOW": "#d9d9d9", "SIM-HIFI": "#9ecae1", "SIM-DATA": "#c7e9c0", "HIL": "#fdae6b",
            "SCALED": "#f16913", "CLOSED": "#a63603", "ROAD": "#4a1486"}
    for t in tiers:
        v = np.array([sum(s in S.split(r["simulator"]) and r["validation_tier"] == t for r in R) for s in top])
        hatch = {"SIM-DATA": "....", "HIL": "////"}.get(t, "")      # second cue where greyscale tones are close
        b.barh(yy, v, left=left, color=tcol[t], height=0.7, label=tl[t].replace("-\n", "-").replace("\n", " "),
               ec="#555555" if hatch else "white", lw=0.3, hatch=hatch)
        left += v
    for k, s in zip(yy, top):
        ph = sum(s in S.split(r["simulator"]) and r["_physical"] for r in R)
        b.text(sims[s] + 1.5, k, f"{sims[s]} ({ph} physical/HIL)", va="center", fontsize=6)
    b.set_yticks(yy); b.set_yticklabels([nm.get(s, s) for s in top])
    b.set_xlim(0, max(sims.values()) * 1.45); b.set_xlabel("Studies using the simulator")
    b.set_title("(b) Simulators and the highest tier reached", loc="left")
    b.legend(ncol=2, frameon=False, fontsize=6, loc="lower right", handlelength=1)
    fig.tight_layout(w_pad=1.5)
    save(fig, "fig08_validation")


# ------------------------------------------------------------------------------------------------
# Figure 9: research-gap landscape. One indicator per gap, computed from the evidence database.
def assumption_share(themes):
    import re
    hi = [r for r in R if S.l3plus(r) and r["guarantee_assumptions"] not in ("NA", "")]
    n = sum(any(re.search(S.ASSUME[t], r["guarantee_assumptions"], re.I) for t in themes) for r in hi)
    return S.pct(n, len(hi)), f"of {len(hi)} L3–L5 studies stating assumptions"


def gap_indicators():
    l4 = [r for r in R if r["safety_level"] == "L4"]
    cm = [r for r in R if S.has(r, "B")]
    nsm = sum(len(r["_safety_metrics"]) <= 1 for r in R)
    perc = sum(any(x in S.split(r["stack"]) for x in ("PERC", "PRED")) for r in R)
    inter = sum(r["traffic"] in ("LEARNED", "HUMAN") for r in R)
    expl = sum(any(u in S.split(r["uncertainty"]) for u in ("EPI", "ALE")) for r in R)
    xai = {row["study_id"]: row["explainability"] for row in csv.DictReader(open(S.W / "extraction" / "xai_codes.csv"))}
    return [
        ("G1", "P1", "Simulation-only studies", S.pct(sum(not r["_physical"] for r in R), N), f"of {N} studies"),
        ("G2", "P1", "L4 studies validated only in simulation", S.pct(sum(not r["_physical"] for r in l4), len(l4)), f"of {len(l4)} L4 studies"),
        ("G15", "P1", "No mapping to an automotive safety standard", S.pct(N - 1, N), "one safety case, B1443"),
        ("G3", "P2", "L3–L5 claims assuming predictable road users or a known model",
         *assumption_share(["predictable other road users", "known or accurate dynamics model"])),
        ("G6", "P2", "No explicit epistemic/aleatoric uncertainty estimate", S.pct(N - expl, N), f"of {N} studies"),
        ("G9", "P3", "Constrained-RL studies without run-time enforcement (<L3)", S.pct(sum(not S.l3plus(r) for r in cm), len(cm)), f"of {len(cm)} CMDP studies"),
        ("G4", "P3", "At most one distinct safety metric", S.pct(nsm, N), f"of {N} studies"),
        ("G8", "P4", "No learning or human-driven surrounding traffic", S.pct(N - inter, N), f"of {N} studies"),
        ("G12", "P5", "Perception/prediction layers not addressed", S.pct(N - perc, N), f"of {N} studies"),
        ("G5", "P6", "Custom (non-shared) simulator", S.pct(sum("CUSTOM" in S.split(r["simulator"]) for r in R), N), f"of {N} studies"),
        ("G7", "P6", "No generalisation test", S.pct(sum(r["generalization"].strip() in ("NONE", "") for r in R), N), f"of {N} studies"),
        ("G10", "P6", "No Safe RL baseline", S.pct(sum("SRL" not in S.split(r["baseline_types"]) for r in R), N), f"of {N} studies"),
        ("G11", "P6", "No code released", S.pct(sum(r["code"] != "Y" for r in R), N), f"of {N} studies"),
        ("G13", "P7", "No explanation produced and inspected", S.pct(sum(xai.get(r["study_id"]) != "VIS" for r in R), N), f"of {N} studies"),
        ("G14", "P7", "No formal verification or specification", S.pct(sum(not S.has(r, "T") for r in R), N), f"of {N} studies"),
    ]


def fig_gaps():
    G = gap_indicators()
    pc = {"P1": OI[5], "P2": OI[4], "P3": OI[0], "P4": OI[6], "P5": OI[2], "P6": OI[1], "P7": GREY}
    pname = {"P1": "P1 Guarantee from simulation to vehicle", "P2": "P2 Robustness to perception/prediction/model error",
             "P3": "P3 Tail-risk and rare-event safety", "P4": "P4 Interactive and VRU traffic",
             "P5": "P5 Safe perception-in-the-loop learning", "P6": "P6 Measurement science",
             "P7": "P7 Certifiable and explainable evidence"}
    import textwrap
    fig, ax = plt.subplots(figsize=(FULL, 5.0))
    yy = np.arange(len(G))[::-1]
    for y, (g, p, lab, v, den) in zip(yy, G):
        ax.plot([0, v], [y, y], color=pc[p], lw=1.4)
        ax.scatter(v, y, s=22, color=pc[p], zorder=3)
        ax.text(v + 3.5, y, f"{v:.1f}%", va="center", fontsize=6.3)
    # gap name wrapped to two lines; the denominator goes into the label so the value annotation stays short
    labels = []
    for g, p, lab, _, den in G:
        labels.append(f"{g} [{p}]  " + "\n".join(textwrap.wrap(f"{lab} ({den})", 44)))
    ax.set_yticks(yy); ax.set_yticklabels(labels, fontsize=6.3, linespacing=1.0)
    ax.set_xlim(0, 118); ax.set_xticks(range(0, 101, 20)); ax.set_xlabel("Share of the relevant studies affected (%)")
    ax.legend(handles=[Line2D([0], [0], color=pc[p], marker="o", lw=1.4, label=pname[p]) for p in pc],
              ncol=2, frameon=False, loc="upper center", bbox_to_anchor=(0.18, -0.09), fontsize=6.3)
    save(fig, "fig09_gaps")
    return G


# ------------------------------------------------------------------------------------------------
# Figure 10: research roadmap (R1-R11 linked to core problems P1-P8)
ROADMAP = [
    ("Short term", "benchmarks and reporting", [
        ("R1", "Common safety evaluation protocol", "P6"), ("R2", "Reproducibility minimum", "P6"),
        ("R3", "Report evidence level and assumptions", "P1, P2")]),
    ("Medium term", "methods that relax assumptions", [
        ("R4", "Perception- and prediction-aware certificates", "P2, P5"),
        ("R5", "Uncertainty-triggered runtime assurance", "P1, P2"),
        ("R6", "Interactive, multi-agent and VRU safety", "P4"),
        ("R7", "State-wise and rare-event safety", "P3"),
        ("R8", "Staged sim-to-real pipelines", "P1")]),
    ("Long term", "assurance and certification", [
        ("R9", "Compositional verification of the safety layer", "P7"),
        ("R10", "Certification-oriented safety cases", "P7"),
        ("R11", "New paradigms inside the safety envelope", "P8")]),
]


def fig_roadmap():
    fig = plt.figure(figsize=(FULL, 4.6))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    cols = ["#c6dbef", "#6baed6", "#2171b5"]
    xs = [0.02, 0.35, 0.68]; w = 0.30
    ax.annotate("", xy=(0.99, 0.93), xytext=(0.01, 0.93),
                arrowprops=dict(arrowstyle="-|>", lw=1.2, color=GREY, mutation_scale=10))
    for (title, sub, items), x, c in zip(ROADMAP, xs, cols):
        box(ax, x, 0.80, w, 0.09, f"{title}\n{sub}", fc=c, ec=c, weight="bold", fs=7.2,
            color="white" if c != cols[0] else INK)
        y = 0.72
        for rid, lab, p in items:
            box(ax, x, y - 0.10, w, 0.10, f"{rid}  {lab}\naddresses {p}", fc="white", ec=c, fs=6.3, lw=0.9)
            y -= 0.118
    ax.text(0.5, 0.015, "Core problems: P1 guarantee from simulation to vehicle; P2 robustness to perception, prediction and "
            "model error; P3 tail-risk safety; P4 interactive traffic; P5 perception-in-the-loop learning; "
            "P6 measurement science; P7 certifiable evidence; P8 new paradigms inside the safety envelope.",
            ha="center", fontsize=6, color=GREY, wrap=True)
    save(fig, "fig10_roadmap")


# ------------------------------------------------------------------------------------------------
# Figure 11: the deployment-readiness chain (mechanism family -> guarantee -> evaluation -> readiness)
READY_C = {"Low": "#d9d9d9", "Low-Medium": "#9ecae1", "Medium": "#4292c6", "Medium-High": "#08519c",
           "High": "#08306b"}


def fig_readiness_chain():
    # primary mechanism grouped into the six review-derived clusters M1-M6 of the taxonomy (Fig. 4): fewer, wider
    # bands than the eleven mechanism families of Table 19, so the chain is easier to follow
    def cluster_of(r):
        return S.CLUSTER.get(r["mech_primary"], "No mechanism of its own")
    M0 = sorted({cluster_of(r) for r in R} - set(S.CLUSTERS))          # M0: no mechanism of its own (5 studies)
    fams = [c for c in S.CLUSTERS + M0 if any(cluster_of(r) == c for r in R)]
    stages = [
        ("Primary safety\nmechanism (cluster)", fams, cluster_of),
        ("Safety\nguarantee", S.GUARANTEE, lambda r: S.GUARANTEE[S.guarantee_index(r)]),
        ("Evaluation\nsetting", S.EVALUATION, lambda r: S.EVALUATION[S.evaluation_index(r)]),
        ("Deployment\nreadiness", S.READINESS, S.readiness),
    ]
    fig = plt.figure(figsize=(FULL, 5.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    xs = [0.28, 0.52, 0.74, 0.84]; nw = 0.012; top, bot, gap = 0.90, 0.06, 0.018
    scale = (top - bot - gap * (len(fams) - 1)) / N
    pos = []
    for k, (title, nodes, fn) in enumerate(stages):
        ax.text(xs[k] + nw / 2 + (0.04 if k == 3 else 0), 0.955, title, ha="center", va="center", fontsize=7, weight="bold")
        y, d = top, {}
        g = gap if k == 0 else (top - bot - N * scale) / max(1, len(nodes) - 1)
        for nd in nodes:
            n = sum(fn(r) == nd for r in R)
            h = n * scale
            d[nd] = [y, y - h]
            if n:
                ax.add_patch(plt.Rectangle((xs[k], y - h), nw, h, fc=INK, ec="none"))
            short = {"E2 High-fidelity or data-driven simulation": "E2 High-fid./data sim.",
                     "E3 Hardware-in-the-loop or scaled vehicle": "E3 HIL or scaled vehicle",
                     "E4 Full-size vehicle (closed course or road)": "E4 Full-size vehicle",
                     "E1 Low-fidelity simulation": "E1 Low-fidelity sim.",
                     "G2 Constraint in expectation": "G2 Constraint (expect.)",
                     "G4 Formal under assumptions": "G4 Formal (assumptions)",
                     "Barrier / Lyapunov certificate (CBF, CLF, CBF-CLF-QP)": "Barrier/Lyapunov certificate",
                     "Shield, mask or rule-based intervention": "Shield, mask or rules",
                     "Constrained RL / safety critic": "Constrained RL / critic",
                     "Reachability / formal verification": "Reachability / formal",
                     "Robust / uncertainty-aware RL": "Robust / uncertainty-aware",
                     "Learning-paradigm extension": "Paradigm extension",
                     "No mechanism of its own": "No own mechanism",
                     "M0 No mechanism (benchmark, representation, assurance case)": "No own mechanism",
                     "M1 Objective shaping": "M1 Objective\nshaping", "M2 Run-time intervention": "M2 Run-time\nintervention",
                     "M3 Control-theoretic certificates": "M3 Control-theoretic\ncertificates", "M4 Formal methods": "M4 Formal\nmethods",
                     "M5 Robustness and uncertainty": "M5 Robustness and\nuncertainty",
                     "M6 Learning-paradigm extensions": "M6 Learning-paradigm\nextensions"}
            lab = f"{short.get(nd, nd)}  ({n})"
            if k == 0:
                ax.text(xs[k] - 0.006, y - h / 2, lab, ha="right", va="center", fontsize=6.4, linespacing=1.05)
            elif k == len(stages) - 1:
                ax.text(xs[k] + nw + 0.006, y - h / 2, lab, ha="left", va="center", fontsize=6.4,
                        weight="bold" if n else "normal", color=INK if n else GREY)
            else:
                nm = short.get(nd, nd)
                two = nm.split(" ", 1)[0] + "\n" + (nm.split(" ", 1)[1] if " " in nm else "") + f" ({n})"
                ax.text(xs[k] - 0.004, y - h / 2, two, ha="right", va="center", fontsize=6, color=INK,
                        linespacing=1.0, bbox=dict(fc="white", ec="none", alpha=0.85, pad=0.5), zorder=5)
            y -= h + g
        pos.append(d)
    # flows, coloured by the readiness the studies finally reach
    t = np.linspace(0, 1, 30); sm = 3 * t ** 2 - 2 * t ** 3
    for k in range(len(stages) - 1):
        fa, fb = stages[k][2], stages[k + 1][2]
        cur_l = {nd: v[0] for nd, v in pos[k].items()}
        cur_r = {nd: v[0] for nd, v in pos[k + 1].items()}
        flows = Counter((fa(r), fb(r), S.readiness(r)) for r in R)
        for a in stages[k][1]:
            for b in stages[k + 1][1]:
                for rd in S.READINESS:
                    n = flows[(a, b, rd)]
                    if not n:
                        continue
                    h = n * scale
                    l0, r0 = cur_l[a], cur_r[b]
                    cur_l[a] -= h; cur_r[b] -= h
                    xa = xs[k] + nw + (xs[k + 1] - xs[k] - nw) * t
                    up = l0 + (r0 - l0) * sm; lo = up - h
                    ax.add_patch(Polygon(np.r_[np.c_[xa, up], np.c_[xa[::-1], lo[::-1]]], fc=READY_C[rd],
                                         ec="none", alpha=0.75))
    ax.legend(handles=[Patch(color=READY_C[rd], label=rd) for rd in S.READINESS], title="Flows shaded by readiness reached",
              title_fontsize=6.2, fontsize=6, ncol=5, frameon=False, loc="lower center", bbox_to_anchor=(0.55, -0.045))
    save(fig, "fig11_readiness_chain")


if __name__ == "__main__":
    fig_prisma(); fig_taxonomy(); fig_architecture(); fig_mechanism_evidence(); fig_evolution()
    fig_applications(); fig_alg_mech(); fig_validation(); fig_gaps(); fig_roadmap(); fig_readiness_chain()
