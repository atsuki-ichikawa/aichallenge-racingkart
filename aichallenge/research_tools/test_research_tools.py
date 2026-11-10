"""計測器のゴールデンテスト（方針 §5）: 既存の結果から summarize/invariant が出す数値が変わらないことを固定する。

host でも動く: python3 -m unittest aichallenge/research_tools/test_research_tools.py
コンテナでは test.sh が pytest で実行する。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bench_common import load_result_dir, parse_stats_lines  # noqa: E402
from invariant_check import THRESH  # noqa: E402

RESULTS = os.path.join(HERE, "results")


def res(name):
    return load_result_dir(os.path.join(RESULTS, name))


def read(name):
    with open(os.path.join(RESULTS, name)) as f:
        return f.read()


def run(script, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, script), *args], capture_output=True, text=True)


class GoldenTest(unittest.TestCase):
    def test_fixed_all_baseline(self):
        r = res("20261109-155004_fixed_all_c388dbf+dirty")
        self.assertEqual(r["laps"], [72.18, 68.90, 69.66])
        self.assertEqual(r["lap_n"], 3)
        self.assertAlmostEqual(r["lap_med_2p"], 69.28)
        self.assertEqual(r["laps_source"], "bench.txt")
        self.assertEqual(r["windows_n"], 27)
        s = r["stats"]
        self.assertEqual(s["windows_used"], 26)
        self.assertEqual(s["solved_rate"], 1.0)
        self.assertEqual((s["rejected_n"], s["fallback_n"], s["maxiter_n"]), (0, 0, 0))
        self.assertAlmostEqual(s["t_p99_max"], 10.94)
        self.assertEqual(s["solves"], 10400)
        self.assertAlmostEqual(s["max_raw_delta_max"], 19.2)
        # 1窓目（ウォームアップ、除外される）: solved 307 / solves 502
        first = parse_stats_lines(read("20261109-155004_fixed_all_c388dbf+dirty/bench.txt"))[0]
        self.assertEqual((first["status"]["solved"], first["solves"]), (307, 502))

    def test_fixed_bc_only_stopped(self):
        r = res("20261109-155527_fixed_bc_only_nocommit")
        self.assertEqual(r["laps"], [])
        self.assertEqual(r["lap_n"], 0)
        self.assertIsNone(r["lap_med_2p"])
        s = r["stats"]
        self.assertAlmostEqual(s["solved_rate"], 0.6757563199336925)
        self.assertEqual((s["rejected_n"], s["fallback_n"], s["maxiter_n"], s["infeasible_n"]), (1667, 3, 2248, 1664))
        self.assertAlmostEqual(s["t_p99_max"], 12.39)
        self.assertEqual(s["solves"], 12065)
        self.assertAlmostEqual(s["max_raw_delta_max"], 32.7)
        first = parse_stats_lines(read("20261109-155527_fixed_bc_only_nocommit/bench.txt"))[0]
        self.assertEqual((first["status"]["maximum iterations reached"], first["rejected"]), (109, 104))

    def test_baseline_a284274_format(self):
        r = res("20261109-154314_baseline_a284274")
        self.assertEqual(r["laps"], [71.38, 67.34, 67.65])
        self.assertAlmostEqual(r["lap_med_2p"], 67.495)
        s = r["stats"]
        self.assertIsNone(s["rejected_n"])          # a284274 の計測行には rejected が無い
        self.assertEqual(s["fallback_n"], 0)
        self.assertEqual(s["solved_rate"], 1.0)
        self.assertAlmostEqual(s["t_p99_max"], 13.66)

    def test_step2_probe_json(self):
        r = res("20261109-173947_step2_probe_0e57977")
        self.assertEqual(r["laps_source"], "awsim_result.json")
        self.assertEqual(r["lap_n"], 3)
        self.assertEqual([round(x, 2) for x in r["laps"]], [72.01, 68.82, 67.91])
        self.assertAlmostEqual(r["lap_med_2p"], 68.36206817626953)
        self.assertEqual(r["penalties"], {"crash": 0, "wall": 0, "over": 0, "block": 0})

    def test_bench_v2_directory(self):
        """bench.sh v2 の結果（autoware.log と JSON がある）: 集計元は autoware.log、周回は JSON。"""
        r = res("20261110-180020_step4_v2b_9818e75+dirty")
        self.assertEqual(r["stats_source"], "autoware.log")
        self.assertEqual(r["windows_n"], 29)
        s = r["stats"]
        self.assertEqual((s["windows_used"], s["solves"]), (28, 11200))
        self.assertAlmostEqual(s["t_p99_max"], 10.86)
        self.assertEqual((r["laps_source"], r["lap_n"]), ("awsim_result.json", 3))
        self.assertAlmostEqual(r["lap_med_2p"], 68.65940475463867)

    def test_synthetic_median_and_penalties(self):
        """lap_med_2p は 2周目以降の『中央値』（平均ではない）。penalty は count を読む。"""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "meta.json"), "w") as f:
                json.dump({"label": "syn", "commit": "0000000", "dirty": False, "status": "completed"}, f)
            with open(os.path.join(d, "awsim_result.json"), "w") as f:
                json.dump({"lap_count": 5, "laps": [70.0, 60.0, 61.0, 90.0, 65.0],
                           "penalty_by_kind": {"crash": {"count": 0, "total_seconds": 0.0}, "wall": {"count": 2, "total_seconds": 7.5},
                                               "over": {"count": 1, "total_seconds": 3.0}, "block": {"count": 0, "total_seconds": 0.0}}}, f)
            r = load_result_dir(d)
        self.assertEqual(r["lap_n"], 5)
        self.assertEqual(r["lap_med_2p"], 63.0)           # median(60, 61, 90, 65) = 63.0、mean なら 69.0
        self.assertEqual(r["penalties"], {"crash": 0, "wall": 2, "over": 1, "block": 0})
        self.assertIsNone(r["stats"])                     # mpc_stats が無い

    def test_invariant_check_thresholds_and_output(self):
        self.assertEqual(THRESH, {"I5_solved_rate_min": 0.95, "I7_t_p99_max_ms": 25.0})
        p = run("invariant_check.py", os.path.join(RESULTS, "20261109-173947_step2_probe_0e57977"))
        self.assertEqual(p.returncode, 0)
        self.assertIn("invariant: fails=0 checked=I5,I6,I7,I8 skipped=I9", p.stdout)
        p = run("invariant_check.py", os.path.join(RESULTS, "20261109-155527_fixed_bc_only_nocommit"))
        self.assertEqual(p.returncode, 1)
        self.assertIn("FAIL I5 solved_rate=0.6757563199336925 < 0.95 (windows 2..27)", p.stdout)
        self.assertIn("FAIL I6 rejected_n=1667 fallback_n=3 (expected 0/0)", p.stdout)
        self.assertIn("invariant: fails=2 checked=I5,I6,I7 skipped=I8,I9", p.stdout)
        p = run("invariant_check.py", os.path.join(RESULTS, "20261110-174519_failsim_9818e75+dirty"))
        self.assertEqual(p.returncode, 3)                  # 何も検査できない（走っていない）

    def test_summarize_rows(self):
        out = run("summarize.py", RESULTS).stdout
        self.assertIn("| fixed_all | c388dbf+dirty | migrated | 3 | 69.28 | monitor | 1.0000 | 0 | 0 | 10.94 | 0 | - | - | - | - | 20261109-155004_fixed_all_c388dbf+dirty |", out)
        self.assertIn("| step4_v2b | 9818e75+dirty | completed | 3 | 68.66 | json | 1.0000 | 0 | 0 | 10.86 | 0 | 0 | 0 | 0 | 0 | 20261110-180020_step4_v2b_9818e75+dirty |", out)
        self.assertIn("| failsim | 9818e75+dirty | aborted | - | - | - | - | - | - | - | - | - | - | - | - | 20261110-174519_failsim_9818e75+dirty |", out)


if __name__ == "__main__":
    unittest.main()
