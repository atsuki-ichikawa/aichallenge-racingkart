#!/usr/bin/env python3
"""同じ label の走行をまとめて、各指標の中央値・最小・最大を出す（実験 report 用。方針 §7「集計はスクリプト」）。

Usage: aggregate_runs.py <label> [results_dir] [--job <ID>]
  status が completed の走行だけを集計し、除外した走行（aborted/void）は別に列挙する。
  出力は Markdown（出典列 = ディレクトリ名）。
"""
import datetime
import statistics
import sys
from pathlib import Path

from bench_common import PENALTY_KINDS, load_result_dir

METRICS = ["lap_n", "lap_med_2p", "solved_rate", "rejected_n", "fallback_n", "t_p99_max", "maxiter_n"] + \
          [f"penalty_{k}_n" for k in PENALTY_KINDS] + ["sim_sec"]


def values(r):
    s = r["stats"] or {}
    pen = r["penalties"] or {}
    m = r["meta"]
    sim_sec = None
    if m.get("sim_start_time") and m.get("sim_end_time"):
        a = datetime.datetime.fromisoformat(m["sim_start_time"])
        b = datetime.datetime.fromisoformat(m["sim_end_time"])
        sim_sec = (b - a).total_seconds()
    return {"lap_n": r["lap_n"], "lap_med_2p": r["lap_med_2p"], "solved_rate": s.get("solved_rate"),
            "rejected_n": s.get("rejected_n"), "fallback_n": s.get("fallback_n"), "t_p99_max": s.get("t_p99_max"),
            "maxiter_n": s.get("maxiter_n"), **{f"penalty_{k}_n": pen.get(k) for k in PENALTY_KINDS}, "sim_sec": sim_sec}


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.4f}" if v <= 1.0 else f"{v:.2f}"
    return str(v)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    label = args[0]
    base = Path(args[1]) if len(args) > 1 else Path(__file__).resolve().parent / "results"
    job = sys.argv[sys.argv.index("--job") + 1] if "--job" in sys.argv else None
    runs = []
    for p in sorted(base.iterdir()):
        if not (p / "meta.json").exists():
            continue
        r = load_result_dir(p)
        if r["label"] != label or (job and r["meta"].get("job") != job):
            continue
        runs.append(r)
    used = [r for r in runs if r["status"] == "completed"]
    excluded = [r for r in runs if r["status"] != "completed"]
    print(f"label={label} job={job or '-'} runs={len(runs)} used={len(used)} excluded={len(excluded)}")
    print()
    print("| 走行 | commit | plan_commit | " + " | ".join(METRICS) + " | 出典 |")
    print("|---|---|---|" + "---|" * len(METRICS) + "---|")
    for r in used:
        v = values(r)
        print(f"| {r['meta'].get('run_index', '-')} | {r['commit']}{'+dirty' if r['dirty'] else ''} | {(r['meta'].get('plan_commit') or '-')[:7]} | "
              + " | ".join(fmt(v[k]) for k in METRICS) + f" | {r['dir']} |")
    print()
    print("| 指標 | 中央値 | 最小 | 最大 | n |")
    print("|---|---|---|---|---|")
    for k in METRICS:
        xs = [values(r)[k] for r in used]
        xs = [x for x in xs if x is not None]
        if not xs:
            print(f"| {k} | - | - | - | 0 |")
            continue
        print(f"| {k} | {fmt(statistics.median(xs))} | {fmt(min(xs))} | {fmt(max(xs))} | {len(xs)} |")
    if excluded:
        print()
        print("除外した走行:")
        for r in excluded:
            print(f"- {r['dir']}: status={r['status']} reason={r['meta'].get('reason', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
