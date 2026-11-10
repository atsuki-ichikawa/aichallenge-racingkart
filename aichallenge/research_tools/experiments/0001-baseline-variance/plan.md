# experiments/0001-baseline-variance — ベースラインのばらつき幅（事前登録）

| 項目 | 内容 |
|---|---|
| ID | 0001（方針 §10 手順6） |
| 目的 | 研究のベースライン（修正版 MPC）を**同一条件で5回**走らせ、周回タイムとソルバー指標のばらつき幅を測る。以後の L2/L4 比較の「走行数」「予算」「不変条件の閾値」を決める根拠にする |
| 仮説 | 無し（計測のみ。改善の主張はしない） |
| 変えるパラメータ | 無し。制御コードは commit `c388dbf`（タグ `baseline-20261109`）のまま。`config.yaml` もそのコミットの値（v_max 20、ay_max 6.5、Q [3e6, 9e7, 1e5]、steering_tire_angle_gain_var 1.639） |
| 条件 | `make dev`（`simulator_scripts/dev.sh`: 1台・周回無制限・count 開始・camera/lidar off）、290 秒、rosbag 併用（bench.sh v2 の既定）、ホストは研究室 PC（GPU 描画）。走らせ方は `run_queue.sh` のジョブ `c388dbf baseline_var 5 plan=…`（専用 worktree、計測器は main 側の bench.sh v2） |
| 指標（`bench_common.py` の定義） | `lap_n`、`lap_med_2p`（JSON の laps の 2 周目以降の中央値）、`solved_rate`、`rejected_n`、`fallback_n`、`t_p99_max`、`maxiter_n`、`penalty_{crash,wall,over,block}_n`、1 走行の実時間（meta.json の `sim_start_time`→`sim_end_time`） |
| 回数 | 5 回連続（queue ジョブ 1 件、n=5） |
| 除外基準 | bench.sh が `aborted` または `void` にした走行、LAP 1 が始まらない走行、AWSIM の異常終了。除外した走行も report に「除外」として残す。除外が 2 回以上なら追加で走らせず、原因を journal に書いて私が判断する |
| 出す値 | 各指標の **中央値・最小・最大**（5 走行）、1 走行の実時間の中央値。集計は `aggregate_runs.py baseline_var` の出力をそのまま report に貼る |
| 決めること（私が決定記録に書く） | (1) L2/L4 比較の走行数（現行の決定 ②: L2 3 本、L4 A/B 各 3 本）を維持するか。(2) §6 の 1 日の予算（1 走行の実時間から）。(3) 不変条件の閾値: I7 の t_p99 上限（暫定 25 ms）、I9 の「悪化幅 ≤ ベースライン分布の幅」の幅＝`lap_med_2p` の最大−最小。(4) 旧ベースライン `20261109-155004_fixed_all_c388dbf+dirty`（commit 推定・dirty・lap_monitor 系）を本実験の 5 走行で置き換えるか |
| 走る前のコミット | この plan.md をコミットしてから走る（bench.sh が `plan_commit` を meta.json に記録する） |
| 日時 | 2026-11-10 夕方（日中予算の内。本日の AWSIM 使用は開始時点で約 21 分） |
