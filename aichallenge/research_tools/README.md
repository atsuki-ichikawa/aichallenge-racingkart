# research_tools

研究用の計測ツール（方針の「計測器」= LM 層。変更の diff は人間が全文読む）。コンテナからは `/aichallenge/research_tools` として見えます。

## 1走行を記録する: `bench.sh`

```
aichallenge/research_tools/bench.sh <label> [秒]      # 既定 290 秒。約5〜6分かかる
```

`make down → make dev → 走行 → make down` を行い、結果を **`results/<日時>_<label>_<commit>[+dirty]/`** に残す。
標準出力は旧 bench.sh と同じ（LAP 行と `[mpc_stats]` 末尾 40 行）で、`bench.txt` にも入る。最後に `RESULT_DIR=... status=...` を出す。

| ファイル | 中身 |
|---|---|
| `meta.json` | 開始時に書き、終了時に `status` を追記。`completed` / `aborted`（起動失敗など。結果ファイルは書かない）/ `void`（走行中に MPC.py・mpc_controller.py・config.yaml が変わった）。commit、dirty、開始終了時刻、load average、3ファイルの sha256（開始・終了）、`param_override`、`params_changed_during_run`、`lap_n`、`invariant_rc`、rosbag の場所 |
| `bench.txt` | 旧形式の本文 |
| `config.yaml` | 走行時の config.yaml のコピー |
| `params_runtime.yaml` / `params_runtime_end.yaml` | 走行開始直後／終了直前の `ros2 param dump /mpc_controller` |
| `param_diff.txt` | `compare_params.py` の出力（config.yaml と実行時パラメータの差） |
| `awsim_result.json` / `awsim_summary.json` | `make down` 後に AWSIM が書く `aichallenge/d1-result-details.json` / `result-summary.json` のコピー（元は .gitignore に当たる）。前回の値を拾わないよう mtime が進んだときだけコピー |
| `autoware.log` / `awsim.log` | `output/<run>/` からのコピー（autoware.log は sha256 を meta に記録） |
| `invariant.txt` | `invariant_check.py` の出力 |
| `git_diff.patch` | 作業ツリーが dirty のときだけ |
| `make_dev.log` / `make_rosbag.log` | 起動コマンドの出力 |

- rosbag は `output/<run>/d1/rosbag2_all/` に残る（git には入れない。`meta.json` の `rosbag_dir`）。`BENCH_ROSBAG=0` で録らない。
- 走行中は `research_tools/.bench.lock` がある。他の重い作業（ビルド・pytest・`make`・`docker compose`）は **`wait_bench.sh` で待ってから**行う。
- 開始時に compose project `aichallenge` のコンテナが1つでもあれば起動しない（終了コード 5）。前回の残骸なら `make down` してから。
- 走行中に simulator/autoware のコンテナが作り直されたら（別の `make dev` など）aborted にする。
- `BENCH_MAKE=false` にすると `make` が失敗したときの経路を試せる（AWSIM は起動しない）。
- `BENCH_ROOT=<別の checkout>` でそのツリーを走らせられる（計測器＝このディレクトリの bench.sh と python、lap_monitor.py も main の版をコンテナにマウント）。`run_queue.sh` がこれを使う。meta.json の `root`・`tools_commit`・`tools_dirty`・`sha256_tools` で「どのコードを、どの計測器で」が分かる。
- 結果ディレクトリは削除・上書き・ラベル変更しない（親 CLAUDE.md の規則）。

## 待つ・並べる: `wait_bench.sh` / `run_queue.sh`

```
aichallenge/research_tools/wait_bench.sh [timeout_sec]     # .bench.lock が消えるまで待つ（0 = 無期限）。終了コード 1 = 時間切れ
echo "<commit> <label> [<n>] [<秒>] [--explore]" > aichallenge/research_tools/queue/T-0001.job
aichallenge/research_tools/run_queue.sh [--once] [--poll 30] # queue/ を古い順に直列で消化。多重起動は flock で拒否
```

- `run_queue.sh` は専用 worktree `../aichallenge-queue` にジョブの commit を checkout し、**このディレクトリの bench.sh** を `BENCH_ROOT=worktree` で n 回走らせる。結果はここの `results/`。
- worktree は初回に自動で作る（build/・install/ をコピー、AWSIM はハードリンク、.env はリンク）。C++・msg・CMake など、コピーした build/ に反映されない変更が commit に含まれていればジョブは failed（`要リビルド`）。Python・yaml・csv の変更だけなら走る。
- ジョブの記録は `queue/done/`・`queue/failed/` の `.job` ファイル（解決した commit、各回の終了コードと結果ディレクトリ、completed 回数、失敗理由）。詳細は `queue/README.md`。
- `queue/STOP` を置くと今の走行の後で止まる。
- 事前登録: ジョブ行に `plan=<plan.md のパス>` を付けると bench.sh が plan.md の最終コミットと sha256 を meta.json に記録する。未コミット／dirty なら `--explore` でない限り走らない（方針 §7）。plan.md は `experiments/<ID>/plan.md` に置く。

## 検査する: `test.sh`

```
aichallenge/research_tools/test.sh        # bench の走行中なら待ってから、コンテナ内で 3 段を実行。終了コード 0 = 全部通った
```

1. `multi_purpose_mpc_ros/test/test_mpc_core.py` を **ノードと同じ `.venv` の python**（osqp 0.6.7.post1）で unittest。修正 (a)(b)(c) の振る舞い3本。地図や経路は使わず、直線の偽経路と偽 OSQP で検査する
2. `multi_purpose_mpc_ros/test/` 全体を system python の pytest（osqp 1.0.5。既存の v2x テストも含む）
3. `test_research_tools.py`（計測器のゴールデンテスト。results/ の既存5件から出る数値を固定）。host でも `python3 -m unittest aichallenge/research_tools/test_research_tools.py` で動く

pre-commit には ruff（check のみ、対象は research_tools と test_mpc_core.py だけ）を入れてある: `pre-commit run ruff-check --all-files`

## 集計する: `summarize.py` / `invariant_check.py`

```
python3 aichallenge/research_tools/summarize.py            # results/ 全体を Markdown の表に（「出典」列 = ディレクトリ名）
python3 aichallenge/research_tools/invariant_check.py aichallenge/research_tools/results/<run>
```

指標の定義は `bench_common.py` の先頭に書いてある（1窓目の `[mpc_stats]` は除外、`lap_med_2p` は2周目以降の中央値、など）。
`invariant_check.py` の閾値は暫定（手順6 のベースライン5走行で確定）。I9 と I1〜I4 は未実装。

## その他

- `lap_monitor.py`: `/awsim/status` を購読して周回タイムを表示する（bench.sh が使う）
- `compare_params.py <config.yaml> <params_runtime.yaml>`: 差があれば終了コード 1
- `aggregate_runs.py <label> [--job <ID>]`: 同じ label の走行の中央値・最小・最大・1走行の実時間（実験 report 用）

## `results/` の旧結果（2026-11-10 に新形式へ移した）

| ディレクトリ | 元ファイル | 備考 |
|---|---|---|
| `20261109-154314_baseline_a284274/` | `bench_baseline.txt` | 公式サンプルのまま。commit は推定（旧 bench.sh は記録しなかった） |
| `20261109-155004_fixed_all_c388dbf+dirty/` | `bench_fixed_all.txt` | 修正 (a)(b)(c) 全部。コミット前の作業ツリー（推定）。**研究のベースライン** |
| `20261109-155527_fixed_bc_only_nocommit/` | `bench_fixed_bc_only.txt` | 修正 (b)(c) だけ。該当コミット無し（再現不可）。1周目の途中で停止 |
| `20261109-173947_step2_probe_0e57977/` | `bench_step2_probe.*` | 手順2 の確認走行（ベースラインと同条件、JSON 付き） |
| `20261109-174532_step2_dev2_probe_0e57977/` | `bench_step2_dev2_probe.*` | `make dev2` の JSON の出方の確認（bench.sh 不使用） |

いずれも `meta.json` の `status` は `migrated`、`commit_note` に出自を書いてある。
