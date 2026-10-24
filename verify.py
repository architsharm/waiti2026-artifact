"""Recompute headline numbers of the WAITI 2026 paper from the released rows. Standard library only.

    python3 verify.py

Checks recomputed values against the paper's generated macros (paper_numbers.tex, a copy of the
paper's numbers.tex) and against the per-dataset cells of aggregates/camera_ready.json (the file
the paper's appendix tables are generated from). Exits non-zero on any mismatch.

Per-row outputs of the hosted judgment model are not redistributed, so its numbers are checked at
the aggregate level: each judgment-model cell of camera_ready.json must have the row count and the
positive/negative split of the released labels (and of the released dev/test halves, where every
row of the kind is released), and the paper's judgment-model macros must equal those cells.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAC = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}", (HERE / "paper_numbers.tex").read_text()))
CR = json.loads((HERE / "aggregates" / "camera_ready.json").read_text())
FAIL: list[str] = []
N_OK = 0


def load(name: str) -> list[dict]:
    p = HERE / "rows" / f"{name}.jsonl"
    raw = (
        p.read_bytes()
        if p.exists()
        else gzip.decompress((HERE / "rows" / f"{name}.jsonl.gz").read_bytes())
    )
    return [json.loads(line) for line in raw.decode().splitlines()]


def check(what: str, got, want) -> None:
    global N_OK
    if str(got) == str(want):
        N_OK += 1
    else:
        FAIL.append(f"{what}: recomputed {got!r}, paper {want!r}")


def pct(k: int, n: int) -> str:
    return f"{100 * k / n:.1f}"


def counts(rows, flag):
    pos = [r for r in rows if r["label"]]
    neg = [r for r in rows if not r["label"]]
    return sum(1 for r in pos if flag(r)), len(pos), sum(1 for r in neg if flag(r)), len(neg)


def jev_cell(ds: str, rows, key: str = "Judgment model") -> dict:
    """Judgment model, aggregates only: the cell's n/pos/neg must match the released labels."""
    c = CR["per_dataset"][ds][key]
    pos = sum(1 for r in rows if r["label"])
    check(f"{ds} | {key} n/pos/neg vs released labels", (len(rows), pos, len(rows) - pos), (c["n"], c["pos"], c["neg"]))
    return c


def jev_half(kind: str, rows, at: str = "at_0.5") -> dict:
    """The test half's pos/neg in camera_ready.json thresholds must match the released calib_split."""
    t = CR["thresholds"][kind]
    test = [r for r in rows if r["calib_split"] == "test"]
    pos = sum(1 for r in test if r["label"])
    check(f"{kind} test half n/pos/neg vs released calib_split", (len(test), pos, len(test) - pos), (t["n_test"], t[at]["pos"], t[at]["neg"]))
    check(f"{kind} dev half size vs released calib_split", sum(1 for r in rows if r["calib_split"] == "dev"), t["n_dev"])
    return t


def cell(ds: str, tier: str, rows, flag) -> None:
    """Compare tp/pos/fp/neg with a per-dataset cell of camera_ready.json."""
    c = CR["per_dataset"][ds][tier]
    tp, pos, fp, neg = counts(rows, flag)
    check(
        f"{ds} | {tier} tp/pos/fp/neg", (tp, pos, fp, neg), (c["tp"], c["pos"], c["fp"], c["neg"])
    )



# ------------------------------------------------------------------ SQL (Sections 3.1, Table 7)
sql = load("gretel_text_to_sql")
tp, pos, fp, neg = counts(sql, lambda r: r["code_parser_flag"])
check("SQLn", f"{len(sql):,}", MAC["SQLn"])
check("SQLcodeRecall", f"{tp}/{pos}", MAC["SQLcodeRecall"])
check("SQLcodeFP", f"{fp}/{neg}", MAC["SQLcodeFP"])
c = jev_cell("gretel text-to-SQL", sql)
check("SQLjevFP (aggregate)", c["fp"], MAC["SQLjevFP"])
check("SQLjevFPRfull (aggregate)", pct(c["fp"], c["neg"]), MAC["SQLjevFPRfull"])
check("SQLjevAUROC (aggregate)", f"{c['auroc']:.3f}", MAC["SQLjevAUROC"])
t = jev_half("SQL", sql)
check("SQLjevThr (aggregate)", f"{t['t_youden']:.2f}", MAC["SQLjevThr"])
check("SQLjevFPRhalf (aggregate)", t["at_0.5"]["fpr"], MAC["SQLjevFPRhalf"])
check("SQLjevFPRbest (aggregate)", t["at_youden"]["fpr"], MAC["SQLjevFPRbest"])
cell("gretel text-to-SQL", "Code (parser)", sql, lambda r: r["code_parser_flag"])
pb = load("payload_box")
cell("payload-box", "Code (parser)", pb, lambda r: r["code_parser_flag"])
jev_cell("payload-box", pb)

# ------------------------------------------------------------------ AgentDojo (Section 3.2)
ad = [r for r in load("agentdojo") if r["in_paper_unique_calls"]]
tp, pos, fp, neg = counts(ad, lambda r: r["code_parser_flag"])
check("ADn", len(ad), MAC["ADn"])
check("ADpos", pos, MAC["ADpos"])
check("ADparserRecall", f"{tp}/{pos}", MAC["ADparserRecall"])
c = jev_cell("AgentDojo (unique calls)", ad)
check("ADjevRecall (aggregate)", f"{c['tp']}/{c['pos']}", MAC["ADjevRecall"])
check("ADjevFP (aggregate)", f"{c['fp']}/{c['neg']}", MAC["ADjevFP"])
check("ADjevAUROC (aggregate)", f"{c['auroc']:.3f}", MAC["ADjevAUROC"])
jev_half("Agent actions", ad)

# ------------------------------------------------------------------ injection (Sections 3.3, Tables 4 and 5)
NAMES = {
    "deepset": "deepset",
    "spml": "SPML",
    "yanismiraoui": "yanismiraoui",
    "trustairlab": "TrustAIRLab",
    "notinject": "NotInject",
}
inj = {k: load(k) for k in NAMES}
for k, ds in NAMES.items():
    cell(ds, "Code (patterns)", inj[k], lambda r: r["code_patterns_flag"])
    cell(ds, "PIGuard", inj[k], lambda r: r["piguard_flag"])
    cell(ds, "ProtectAI", inj[k], lambda r: r["protectai_flag"])
ni = inj["notinject"]
check("INJni", len(ni), MAC["INJni"])
check("Table 4 PIGuard FP NotInject", f"{sum(r['piguard_flag'] for r in ni)}/339", "39/339")
check("Table 4 ProtectAI FP NotInject", f"{sum(r['protectai_flag'] for r in ni)}/339", "148/339")
dp, tr = inj["deepset"], inj["trustairlab"]
check("OVdeepN", len(dp), MAC["OVdeepN"])
check("OVdeepIn", sum(r["in_piguard_train"] for r in dp), MAC["OVdeepIn"])
unseen = [r for r in dp if not r["in_piguard_train"]]
check("OVdeepUnseen", len(unseen), MAC["OVdeepUnseen"])
check("OVdeepPigRec", pct(*counts(unseen, lambda r: r["piguard_flag"])[:2]), MAC["OVdeepPigRec"])
check("OVdeepPaiRec", pct(*counts(unseen, lambda r: r["protectai_flag"])[:2]), MAC["OVdeepPaiRec"])
check("OVtrustIn", sum(r["in_piguard_train"] for r in tr), MAC["OVtrustIn"])
check("OVtrustInPos", sum(r["in_piguard_train"] and r["label"] for r in tr), MAC["OVtrustInPos"])
check("OVtrustJack", sum(r["in_jackhhao_train"] for r in tr), MAC["OVtrustJack"])
u = [r for r in tr if not r["in_piguard_train"]]
c = counts(u, lambda r: r["piguard_flag"])
check("OVtrustPigRec", pct(c[0], c[1]), MAC["OVtrustPigRec"])
check("OVtrustPigFPR", pct(c[2], c[3]), MAC["OVtrustPigFPR"])
u = [r for r in tr if not r["in_jackhhao_train"]]
c = counts(u, lambda r: r["protectai_flag"])
check("OVtrustPaiRec", pct(c[0], c[1]), MAC["OVtrustPaiRec"])
check("OVtrustPaiFPR", pct(c[2], c[3]), MAC["OVtrustPaiFPR"])
adapt = load("adaptive_attempts")
esc = [r for r in adapt if r["escaped_shipped_detectors"]]
check("INJpos (escapes)", len(esc), MAC["INJpos"])
check("Table 4 patterns recall on escapes", sum(r["code_shipped_flag"] for r in esc), 0)
check("OVescIn", sum(r["in_piguard_train"] for r in esc), MAC["OVescIn"])
check("INJseeds", len({r["seed_id"] for r in esc}), MAC["INJseeds"])


# recomputed classifier probabilities (Sec. 3.3, Tables 7 and 8): reproduction, AUROC and TPR at 1% FPR
def auroc(scores, labels) -> float:
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    pairs = sorted(zip(scores, labels), key=lambda t: t[0])
    rank_sum, i = 0.0, 0
    while i < len(pairs):
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        rank_sum += (i + 1 + j) / 2 * sum(1 for _, y in pairs[i:j] if y)
        i = j
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def tpr1(scores, labels) -> str:
    pos, neg, best = sum(labels), len(labels) - sum(labels), 0
    for t in sorted(set(scores), reverse=True):
        tp = sum(s >= t and y for s, y in zip(scores, labels))
        fp = sum(s >= t and not y for s, y in zip(scores, labels))
        if fp / neg <= 0.01 and tp > best:
            best = tp
    return f"{100 * best / pos:.1f}"


allinj = [r for k in NAMES for r in inj[k]]
for tier, tag in (("piguard", "Pig"), ("protectai", "Pai")):
    key = f"{tier}_score_recomputed"
    check(f"CSrep{tag}", f"{sum((r[key] >= 0.5) == r[tier + '_flag'] for r in allinj):,}", MAC[f"CSrep{tag}"])
    y = [r["label"] for r in allinj]
    s = [r[key] for r in allinj]
    check(f"CS{tag}AUROC", f"{auroc(s, y):.3f}", MAC[f"CS{tag}AUROC"])
    check(f"CS{tag}TPRone", tpr1(s, y), MAC[f"CS{tag}TPRone"])
    rows_t = inj["trustairlab"]
    check(f"CS{tag}TrustTPRone", tpr1([r[key] for r in rows_t], [r["label"] for r in rows_t]), MAC[f"CS{tag}TrustTPRone"])
    k6 = {"deepset": "deepset", "spml": "SPML", "trustairlab": "TrustAIRLab"}
    for k, ds in k6.items():
        a = auroc([r[key] for r in inj[k]], [r["label"] for r in inj[k]])
        check(f"Table 7 AUROC {ds} {tier}", f"{a:.3f}", f"{json.loads((HERE / 'aggregates' / 'classifier_scores.json').read_text())['per_set'][ds][tier]['auroc']:.3f}")
check("CSrepN", f"{len(allinj):,}", MAC["CSrepN"])

# per-suite provenance (Table 3): suites add up to the totals of the summary file
PS = json.loads((HERE / "aggregates" / "provenance_suites.json").read_text())["settings"]
PSUM = json.loads((HERE / "aggregates" / "agentdojo_inferred_provenance_summary.json").read_text())["conditions"]
for name, cond in (("session", "inferred_session_taint"), ("argument", "inferred_argument_taint"),
                   ("session, read-only exempt", "inferred_session_taint_tiered"),
                   ("argument, read-only exempt", "inferred_argument_taint_tiered")):
    per = PS[name]["per_suite"]
    for m, field in (("BU", "benign_tasks_allowed"), ("ACT", "acting_calls_contained")):
        got = f"{sum(v[m][0] for v in per.values())}/{sum(v[m][1] for v in per.values())}"
        check(f"Table 3 {name} {m} total", got, PSUM[cond][field]["fraction"])
PSN = json.loads((HERE / "aggregates" / "prompt_sensitivity.json").read_text())["kinds"]
check("PSNansFlipA (aggregate)", f"{PSN['Answerability']['A']['flip_rate_at_0.5']:.1f}", MAC["PSNansFlipA"])
check("PSNansFlipB (aggregate)", f"{PSN['Answerability']['B']['flip_rate_at_0.5']:.1f}", MAC["PSNansFlipB"])
check("PSNansFlipRe (aggregate)", f"{PSN['Answerability']['stored']['flip_rate_at_0.5']:.1f}", MAC["PSNansFlipRe"])
check("PSNsqlFlipMax (aggregate)", f"{max(PSN['SQL'][c]['flip_rate_at_0.5'] for c in ('A', 'B')):.1f}", MAC["PSNsqlFlipMax"])
check("PSNrows (aggregate)", PSN["SQL"]["rows"], MAC["PSNrows"])
check("PStravelSRO", "{}/{}".format(*PS["session, read-only exempt"]["per_suite"]["travel"]["BU"]), MAC["PStravelSRO"])

# ------------------------------------------------------------------ answerability (KUQ; CoCoNot rows not released)
kuq = load("kuq")
cell("KUQ", "Code (rules)", kuq, lambda r: r["code_rules_flag"])
c = jev_cell("KUQ", kuq)
coc = CR["per_dataset"]["CoCoNot"]["Judgment model"]  # CoCoNot rows are not released
check("ANSjevRecall (aggregate)", pct(c["tp"] + coc["tp"], c["pos"] + coc["pos"]), MAC["ANSjevRecall"])
check("ANSjevFPR (aggregate)", pct(c["fp"] + coc["fp"], c["neg"] + coc["neg"]), MAC["ANSjevFPR"])

# ------------------------------------------------------------------ PII (Section 3.4)
pii = load("presidio") + load("gretel_pii") + load("tab")
check("PIIn", f"{len(pii):,}", MAC["PIIn"])
clean = [r for r in pii if not r["label"] and not r["has_any_labelled_span"]]
check("PIIclean", len(clean), MAC["PIIclean"])
check(
    "PIIdirty",
    sum(1 for r in pii if not r["label"] and r["has_any_labelled_span"]),
    MAC["PIIdirty"],
)
tab = [r for r in pii if r["in_paper_table"]]
c = counts(tab, lambda r: r["code_native_flag"])
check("PIIcodeRecall", pct(c[0], c[1]), MAC["PIIcodeRecall"])
check("PIIcodeFPR", pct(c[2], c[3]), MAC["PIIcodeFPR"])
jc = []
for name, ds in (("presidio", "presidio"), ("gretel_pii", "gretel PII"), ("tab", "TAB")):
    rr = [r for r in tab if r["dataset"] == name]
    cell(ds, "Code (native)", rr, lambda r: r["code_native_flag"])
    jc.append(jev_cell(ds, rr))
check("PIIjevRecall (aggregate)", pct(sum(c["tp"] for c in jc), sum(c["pos"] for c in jc)), MAC["PIIjevRecall"])
check("PIIjevFPR (aggregate)", pct(sum(c["fp"] for c in jc), sum(c["neg"] for c in jc)), MAC["PIIjevFPR"])
t = jev_half("PII presence", tab)
check("PIIjevFPRhalf (aggregate)", t["at_0.5"]["fpr"], MAC["PIIjevFPRhalf"])
check("PIIjevFPRbest (aggregate)", t["at_youden"]["fpr"], MAC["PIIjevFPRbest"])

# ------------------------------------------------------------------ entitlement
pl = load("privacylens")
check("ENTn", len(pl), MAC["ENTn"])
c = jev_cell("PrivacyLens", pl)
check("ENTjevRecall (aggregate)", pct(c["tp"], c["pos"]), MAC["ENTjevRecall"])

# ------------------------------------------------------------------ policy rules (Section 3.5)
sp = load("safepyramid")
jev_cell("SafePyramid (3,000 conv.)", sp)
s6 = [r for r in sp if r["in_600_subset"]]
check("SPn", f"{len(s6):,}", MAC["SPn"])
jev_cell("SafePyramid (600 conv.)", s6)
cell("SafePyramid (600 conv.)", "LLM", s6, lambda r: r["llm_flag"])
for lv, tag in (("L0", "Lzero"), ("L2", "Ltwo")):
    rr = [r for r in s6 if r["level"] == lv]
    check(
        f"SPllm{tag}",
        pct(sum(r["llm_flag"] == r["label"] for r in rr), len(rr)),
        MAC[f"SPllm{tag}"],
    )
jev_half("Policy rules", sp)

# ------------------------------------------------------------------ trajectories (ATBench corpora; R-Judge rows not released)
tc = {}
for name, ds in (
    ("atbench", "ATBench"),
    ("atbench500", "ATBench500"),
    ("atbench_claw", "ATBench-Claw"),
):
    tc[ds] = jev_cell(ds, load(name))
check("TRatUnsafe (aggregate)", f"AUROC {tc['ATBench']['auroc']:.3f}", MAC["TRatUnsafe"])
check("TRatfiveUnsafe (aggregate)", f"AUROC {tc['ATBench500']['auroc']:.3f}", MAC["TRatfiveUnsafe"])

# ------------------------------------------------------------------ commitments
jev_cell("refund replies (in-house)", load("refund_replies"))

print(f"{N_OK} checks passed, {len(FAIL)} failed")
for f in FAIL:
    print("  MISMATCH", f)
sys.exit(1 if FAIL else 0)
