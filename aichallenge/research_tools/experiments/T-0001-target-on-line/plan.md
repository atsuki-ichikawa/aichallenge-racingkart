# T-0001 — MPC の横位置の目標を CSV の線に合わせる（実験カード兼・事前登録）

状態: 2026-11-17 にユーザーが空欄を書き、右辺は ア に決め、下の「良しの基準（数字）」を承認した。走る前にこの plan.md をコミットする（事前登録）。変更は commit `f0713cf`（ブランチ `exp/T-0001`）。

| 項目 | 内容 | 出典 |
|---|---|---|
| 意図（ユーザーが決めた） | MPC の横位置の目標を「帯の真ん中」から「CSV の線の上」に変える（案 A）。層 L4、ブランチ `exp/T-0001` | `docs/racing_line.md` |
| 選んだ理由・物理的な意味・仮説 | レースで大事なのはレーシングラインなので | — |
| 変えてよい | `core/MPC.py` 227 行 `xr[self.nx::self.nx] = (lb + ub) / 2` の右辺だけ。1変更1コミット | `core/MPC.py` 227・263 行 |
| 右辺の候補（私が1つ選ぶ） | ア: `0`（完全に線の上）／イ: `np.clip(0, lb, ub)`（線が帯の外に出る所だけ帯の端）／ウ: `a * (lb + ub) / 2`（a = 0 が線、1 が今。a の値は私が決めてコードに直接書く） → アで| — |
| やらないこと | `width` 2.30 などの安全値、CSV の線、`Q`・`QN` の重み、`[mpc_stats]` の形式、227 行以外の変更 | `aichallenge-racingkart/CLAUDE.md` |
| 測るもの | `lap_n`、`lap_med_2p`、`solved_rate`、`rejected_n`、`fallback_n`、`t_p99_max`、`maxiter_n`、ペナルティ4種。加えて車と線の距離・壁からの最短距離（既存の `track_vs_line.py` で rosbag を読むだけ） | `bench_common.py`、`docs/racing_line_evidence/track_vs_line.py` |
| 走行数 | A（変更前。制御コードは `c388dbf` と同じ）と B（変更後）を交互に各3、計6。約 32 分。`make dev`、290 秒、rosbag あり、`run_queue.sh` 経由 | `docs/decisions/0002` (1)(2) |
| 何をもって良しとするか | レーシングラインにきちんと沿って走っている。参考: 基準5走行の `lap_med_2p` は 68.44〜69.35 秒（幅 0.91） | `experiments/0002-baseline-awsim1112/report.md` |
| 打ち切り・除外 | 6走行で終わり、追加しない。B でペナルティか invariant（I5〜I8）の失敗が出たら残りを止めて報告し、続けるかは私が決める。除外は 0001 と同じ（`aborted`・`void`、LAP 1 が始まらない、AWSIM の異常終了） | `experiments/0001-baseline-variance/plan.md` |
| 確かめ方 | 走る前: 未確認 1 を確かめる → `test.sh` → 私が全文 diff を読み `docs/approvals.md` に1行 → この plan.md をコミット。走った後: `invariant_check.py`、`aggregate_runs.py` の出力を貼る、反証レビュー1本 | `aichallenge-racingkart/CLAUDE.md` の L4 行 |

## 良しの基準（数字。案は AI、2026-11-17 にユーザーが「その案でよい」と承認）
- 量: 各走行の「車と線の距離の中央値」。`docs/racing_line_evidence/track_vs_line.py` の出力行 `car <-> CSV line |e| [m]: median` の値（sha256 `2098401a…`。入力はその走行の rosbag、`meta.json` の `rosbag_dir`）。
- 基準: **B の3走行のどの値も、A の3走行の最小値より小さい。かつ6走行すべてで invariant の失敗 0（I8 = ペナルティ 0 を含む）。**
- 除外が出て A・B のどちらかが3本そろわないときは判定しない。どうするかは私が決める。
- 走らせ方: ジョブ6件（各1走行）を A・B・A・B・A・B の順に `run_queue.sh --once`。A = commit `c05afd0`（`f0713cf` の親。ラベル `T-0001_A`）、B = commit `f0713cf`（ラベル `T-0001_B`）。

## 走る前に確かめたこと（2026-11-17）
「帯」= 車の中心が入ってよい範囲。左右の壁からそれぞれ 1.63 m 内側に引いた2本の境界の間（道幅から両側 1.63 m ずつ削ったもの）。

| 事柄 | 結果 | 出典 |
|---|---|---|
| 制御器がならした後の線（351 点）が帯の内側にあるか | 帯の外に出る点 0、帯がつぶれる点 0 | `docs/racing_line_evidence/band_check_smoothed.out`（制御器の `Map`・`ReferencePath` をそのまま使って計算。走行なし） |
| 線から帯の端までの余裕 | 左は最小 0.10 m・中央値 1.84 m、右は最小 0.29 m・中央値 1.68 m | 同上 |
| 右辺の選択 | ア（`0`、完全に線の上）。ユーザーが決めた | この表の上の「右辺の候補」 |

## 未確認
- 既存の単体テスト（`test_mpc_core.py`）は左右対称の帯（±3 m）を使うので、真ん中と線が同じ位置になる。この変更の前後で値が変わらず、変更そのものは検査していない。
