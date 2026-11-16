# experiments/0002-baseline-awsim1112 — 結果（report）

plan: [plan.md](plan.md)（コミット cbada61）。走行は 2026-11-16 18:51〜19:17 JST、queue ジョブ `T-0002-baseline-awsim1112`。
AWSIM: 公式の現行版（配布ファイル 2026-11-12 更新、DLL sha256 `77419b89dea5…`、meta.json の `awsim_dir.bytes` = 668456975）。制御コードは commit `c388dbf`、dirty 無し。
5 走行とも `status: completed`、invariant（I5〜I8）失敗なし、除外なし。

## 集計（スクリプトの出力をそのまま貼る）

```
$ python3 aichallenge/research_tools/aggregate_runs.py baseline_awsim1112 --job T-0002-baseline-awsim1112
label=baseline_awsim1112 job=T-0002-baseline-awsim1112 runs=5 used=5 excluded=0

| 走行 | commit | plan_commit | lap_n | lap_med_2p | solved_rate | rejected_n | fallback_n | t_p99_max | maxiter_n | penalty_crash_n | penalty_wall_n | penalty_over_n | penalty_block_n | sim_sec | 出典 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | c388dbf | cbada61 | 3 | 68.67 | 1.0000 | 0 | 0 | 10.98 | 0 | 0 | 0 | 0 | 0 | 310.00 | 20261116-185136_baseline_awsim1112_c388dbf |
| 2 | c388dbf | cbada61 | 3 | 69.20 | 1.0000 | 0 | 0 | 10.88 | 0 | 0 | 0 | 0 | 0 | 310.00 | 20261116-185650_baseline_awsim1112_c388dbf |
| 3 | c388dbf | cbada61 | 3 | 68.44 | 1.0000 | 0 | 0 | 10.85 | 0 | 0 | 0 | 0 | 0 | 311.00 | 20261116-190204_baseline_awsim1112_c388dbf |
| 4 | c388dbf | cbada61 | 3 | 69.22 | 1.0000 | 0 | 0 | 10.73 | 0 | 0 | 0 | 0 | 0 | 310.00 | 20261116-190718_baseline_awsim1112_c388dbf |
| 5 | c388dbf | cbada61 | 3 | 69.35 | 1.0000 | 0 | 0 | 11.07 | 0 | 0 | 0 | 0 | 0 | 310.00 | 20261116-191232_baseline_awsim1112_c388dbf |

| 指標 | 中央値 | 最小 | 最大 | n |
|---|---|---|---|---|
| lap_n | 3 | 3 | 3 | 5 |
| lap_med_2p | 69.20 | 68.44 | 69.35 | 5 |
| solved_rate | 1.0000 | 1.0000 | 1.0000 | 5 |
| rejected_n | 0 | 0 | 0 | 5 |
| fallback_n | 0 | 0 | 0 | 5 |
| t_p99_max | 10.88 | 10.73 | 11.07 | 5 |
| maxiter_n | 0 | 0 | 0 | 5 |
| penalty_crash_n | 0 | 0 | 0 | 5 |
| penalty_wall_n | 0 | 0 | 0 | 5 |
| penalty_over_n | 0 | 0 | 0 | 5 |
| penalty_block_n | 0 | 0 | 0 | 5 |
| sim_sec | 310.00 | 310.00 | 311.00 | 5 |
```

## 旧版の AWSIM（experiments/0001）と並べる

中央値（最小〜最大、幅）。計算は report 作成時の python（`bench_common.load_result_dir`）。

| 量 | 旧版 AWSIM（0001、5走行） | 現行版 AWSIM（0002、5走行） | 中央値の差（新 − 旧） |
|---|---|---|---|
| lap_med_2p [s] | 68.97（68.70〜69.21、幅 0.52） | 69.20（68.44〜69.35、幅 0.91） | +0.22 s |
| 1周目 [s] | 72.66（72.58〜73.66、幅 1.08） | 72.97（72.11〜73.23、幅 1.12） | +0.30 s |
| t_p99_max [ms] | 10.90（10.83〜11.10、幅 0.27） | 10.88（10.73〜11.07、幅 0.34） | -0.02 ms |

出典: 旧 = `results/20261110-19*_baseline_var_c388dbf/`、新 = `results/20261116-1[89]*_baseline_awsim1112_c388dbf/`。

## 次に私（人間）が決めること

以後の基準をこの5走行にするか。
