# queue — run_queue.sh のジョブ置き場

- `<ID>.job` を置く（1行: `<commit> <label> [<n>] [<duration_sec>] [--explore]`。n は 1〜10、秒は 30〜900）。`run_queue.sh` が古い順に消化する
- `running/` 実行中、`done/` completed が 1 回以上、`failed/` 準備で失敗・completed 0 回・2 回連続で aborted・前回の run_queue の途中停止（`# reason:` 行に理由）
- 同じ ID を再投入しても過去の記録は上書きせず `<ID>.<日時>.job` として残る
- `STOP` ファイルを置くと今のジョブの後で止まる
- 未着手の `.job`・`running/`・`run_queue.log` は git に入れない。`done/`・`failed/` は記録として残す（結果ディレクトリ名が書いてある）
