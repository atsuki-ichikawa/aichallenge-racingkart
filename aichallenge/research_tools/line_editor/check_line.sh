#!/usr/bin/env bash
# check_line.sh <csv> — 手で引いた線を、制御器と同じ計算で確かめる（コンテナ内で check_line.py を回す。走行はしない）。
# RACINGKART_DIR: ビルド済み（aichallenge/workspace/install がある）チェックアウト。省略時はこのファイルのあるリポジトリ。
set -eu
csv="$(readlink -f "${1:?使い方: check_line.sh <csv>}")"
[ -f "$csv" ] || { echo "check_line: ファイルが無い: $csv" >&2; exit 2; }
here="$(cd "$(dirname "$0")" && pwd)"
repo="${RACINGKART_DIR:-$(git -C "$here" rev-parse --show-toplevel)}"
if [ -e "$repo/aichallenge/research_tools/.bench.lock" ]; then
    echo "check_line: 走行中（.bench.lock）。終わってから実行してください" >&2; exit 1
fi
pkg=/aichallenge/workspace/src/aichallenge_submit/multi_purpose_mpc_ros
cd "$repo"
CMD="cd $pkg && MPLBACKEND=Agg /aichallenge/workspace/install/multi_purpose_mpc_ros/.venv/bin/python /line_editor/check_line.py '/line_in/$(basename "$csv")'" \
    docker compose run --rm --no-deps -T -v "$here:/line_editor:ro" -v "$(dirname "$csv"):/line_in:ro" autoware-command
