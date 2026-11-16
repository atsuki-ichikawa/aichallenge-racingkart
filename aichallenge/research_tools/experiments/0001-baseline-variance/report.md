# experiments/0001-baseline-variance — 結果（report）

plan: [plan.md](plan.md)（コミット 950bcb3）。走行は 2026-11-10 19:26〜19:52 JST、queue ジョブ `T-0001-baseline-variance`（`queue/done/T-0001-baseline-variance.job`）。
制御コード: commit `c388dbf`（タグ baseline-20261109）、dirty 無し。計測器: bench.sh v2（main 側、commit 950bcb3 時点の作業ツリー）。
5 走行とも `status: completed`、`param_override: false`、`params_changed_during_run: false`、config.yaml の sha256 は開始・終了で同一、invariant（I5〜I8）失敗なし。除外した走行は無し。

## 集計（スクリプトの出力をそのまま貼る）

```
$ python3 aichallenge/research_tools/aggregate_runs.py baseline_var --job T-0001-baseline-variance
label=baseline_var job=T-0001-baseline-variance runs=5 used=5 excluded=0

| 走行 | commit | plan_commit | lap_n | lap_med_2p | solved_rate | rejected_n | fallback_n | t_p99_max | maxiter_n | penalty_crash_n | penalty_wall_n | penalty_over_n | penalty_block_n | sim_sec | 出典 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | c388dbf | 950bcb3 | 3 | 68.85 | 1.0000 | 0 | 0 | 10.83 | 0 | 0 | 0 | 0 | 0 | 311.00 | 20261110-192623_baseline_var_c388dbf |
| 2 | c388dbf | 950bcb3 | 3 | 69.11 | 1.0000 | 0 | 0 | 11.10 | 0 | 0 | 0 | 0 | 0 | 311.00 | 20261110-193137_baseline_var_c388dbf |
| 3 | c388dbf | 950bcb3 | 3 | 68.97 | 1.0000 | 0 | 0 | 10.90 | 0 | 0 | 0 | 0 | 0 | 311.00 | 20261110-193651_baseline_var_c388dbf |
| 4 | c388dbf | 950bcb3 | 3 | 68.70 | 1.0000 | 0 | 0 | 10.88 | 0 | 0 | 0 | 0 | 0 | 311.00 | 20261110-194205_baseline_var_c388dbf |
| 5 | c388dbf | 950bcb3 | 3 | 69.21 | 1.0000 | 0 | 0 | 11.02 | 0 | 0 | 0 | 0 | 0 | 311.00 | 20261110-194719_baseline_var_c388dbf |

| 指標 | 中央値 | 最小 | 最大 | n |
|---|---|---|---|---|
| lap_n | 3 | 3 | 3 | 5 |
| lap_med_2p | 68.97 | 68.70 | 69.21 | 5 |
| solved_rate | 1.0000 | 1.0000 | 1.0000 | 5 |
| rejected_n | 0 | 0 | 0 | 5 |
| fallback_n | 0 | 0 | 0 | 5 |
| t_p99_max | 10.90 | 10.83 | 11.10 | 5 |
| maxiter_n | 0 | 0 | 0 | 5 |
| penalty_crash_n | 0 | 0 | 0 | 5 |
| penalty_wall_n | 0 | 0 | 0 | 5 |
| penalty_over_n | 0 | 0 | 0 | 5 |
| penalty_block_n | 0 | 0 | 0 | 5 |
| sim_sec | 311.00 | 311.00 | 311.00 | 5 |
```

## 幅（同じ5走行から。計算は report 作成時の python、下の表の出典は上の表と同じ 5 ディレクトリ）

| 量 | 値 |
|---|---|
| lap_med_2p の幅 [s] | max-min = 0.52（68.70〜69.21） |
| 1周目 (LAP 1) の幅 [s] | max-min = 1.08（72.58〜73.66）（発車を含むので別物） |
| t_p99_max の幅 [ms] | max-min = 0.27（10.83〜11.10） |
| 1走行の壁時計 [s]（bench.sh 開始→終了） | 中央値 313、313〜313 |
| 5走行の合計 [min]（queue の開始→終了） | 26.2 |

## 読み方の注意（解釈ではなく定義）

- `lap_med_2p` は AWSIM の結果 JSON の 2 周目・3 周目の中央値（= 2 値の平均）。1 周目は発車を含むので別に示した。
- `sim_sec` は `make dev` の完了から `make down` までで、5 走行とも 311 秒（290 秒の監視 ＋ 前後の処理）。
- 旧ベースライン `20261109-155004_fixed_all_c388dbf+dirty` の lap_med_2p は 69.28（lap_monitor 系、commit 推定）。本実験は JSON 系なので同じ土俵ではない（約 0.1 秒のずれがある。env_map 参照）。

## 次に私（人間）が決めること → `docs/decisions/0002`

plan.md の「決めること」(1)〜(4)。候補と数値は決定記録の下書きにある。
