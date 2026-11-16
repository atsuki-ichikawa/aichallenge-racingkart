# experiments/0002-baseline-awsim1112 — AWSIM を公式の現行版に入れ替えた後の基準（事前登録）

| 項目 | 内容 |
|---|---|
| 目的 | AWSIM を 11月9日取得の版から公式の現行版（配布ファイル 2026-11-12 更新、DLL sha256 `77419b89dea5…`）に入れ替えた。同じ制御コードで基準の5走行を取り直し、以後の比較の基準にする |
| 変えたもの | AWSIM 本体だけ。制御コードは commit `c388dbf`、`config.yaml` も同じ。走らせ方も 0001 と同じ（`make dev`、290 秒、rosbag あり、queue ジョブ n=5） |
| 指標 | 0001 と同じ（`lap_n`、`lap_med_2p`、`solved_rate`、`rejected_n`、`fallback_n`、`t_p99_max`、`maxiter_n`、ペナルティ4種、1走行の実時間） |
| 回数 | 5 回連続 |
| 除外基準 | 0001 と同じ（`aborted`・`void`、LAP 1 が始まらない、AWSIM の異常終了。除外も report に残す） |
| 出す値 | 各指標の中央値・最小・最大（`aggregate_runs.py baseline_awsim1112`）。0001 の同じ表と並べる |
| 決めること（私） | 以後の基準をこの5走行にするか。0001（旧版 AWSIM）との差をどう扱うか |
| 既知の差 | 車の物理・指令・ペナルティの処理と `vehicle.yaml` は旧版と同じ。コースのデータファイルは中身が変わっている（`docs/sim_constraints.md` §3） |
