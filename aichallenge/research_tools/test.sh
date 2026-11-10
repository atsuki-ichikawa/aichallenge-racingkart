#!/usr/bin/env bash
# test.sh — 決定論的検査をコンテナ内で実行する（方針 §5）。bench の走行中は wait_bench.sh で待つ。
#   0. host で ruff check（research_tools と test_mpc_core.py。ruff が無ければ飛ばして警告）
#   1. multi_purpose_mpc_ros/test/test_mpc_core.py を **ノードと同じ .venv の python**（osqp 0.6.7）で unittest
#   2. multi_purpose_mpc_ros/test 全体を system python の pytest（osqp 1.0.5。既存の test_v2x_vehicle_tracker.py を含む）
#   3. research_tools/test_research_tools.py（計測器のゴールデンテスト）を pytest
# 使い方: aichallenge/research_tools/test.sh    終了コード: 0 = 全部通った
set -u
tools="$(cd "$(dirname "$0")" && pwd)"
cd "$tools/../.." || exit 1
if command -v ruff >/dev/null 2>&1; then
    echo "== 0. ruff check (host)"
    ruff check "$tools" aichallenge/workspace/src/aichallenge_submit/multi_purpose_mpc_ros/test/test_mpc_core.py || exit 1
else
    echo "== 0. ruff が無いので lint は飛ばす" >&2
fi
"$tools/wait_bench.sh" 0
pkg=/aichallenge/workspace/src/aichallenge_submit/multi_purpose_mpc_ros
venv=/aichallenge/workspace/install/multi_purpose_mpc_ros/.venv/bin/python
CMD="set -e; cd $pkg; echo '== 1. test_mpc_core (.venv python)'; $venv -m unittest test.test_mpc_core; \
     echo '== 2. test/ (system pytest)'; python3 -m pytest -q test; \
     echo '== 3. research_tools golden (pytest)'; cd /aichallenge/research_tools; python3 -m pytest -q test_research_tools.py" \
    timeout 600 docker compose run --rm --no-deps autoware-command 2>&1 | grep -v "^ Container "
exit "${PIPESTATUS[0]}"
