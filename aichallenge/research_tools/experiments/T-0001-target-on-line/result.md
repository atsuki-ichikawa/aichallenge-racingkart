# T-0001 の結果（数字だけ。解釈は書かない）

- 走った数: 2本（A 1本、B 1本）。計画は6本。B の1本目で invariant I6 が失敗し、カードの打ち切り条件で止めた。
- 2026-11-18 にユーザーが「残り4本を走らせずに終える」と決めた。
- 判定: なし（カードの決まり「どちらかが3走行そろわなければ判定しない」による）。

| 走行 | commit | invariant | 車と CSV の線の距離の中央値 [m] | 出典 |
|---|---|---|---|---|
| A | `c05afd0` | 失敗 0 | 0.41 | `results/20261117-131617_T-0001_A_c05afd0/invariant.txt`、`track_vs_line_A.out` 6 行目 |
| B | `f0713cf` | 失敗 1（I6: `rejected_n=15`） | 0.14 | `results/20261117-132131_T-0001_B_f0713cf/invariant.txt`、`track_vs_line_B.out` 6 行目 |

- 距離のコマンドは各 `.out` の1行目。スクリプトは `docs/racing_line_evidence/track_vs_line.py`（sha256 は2行目。計画に書いた値と同じ）。
- I6 の 15 回が起きた場所の調べ: `docs/racing_line_evidence/reject_windows.out`（原因は未確認）。
- 未確認: 各1本なので、走行ごとのばらつきは分からない。
