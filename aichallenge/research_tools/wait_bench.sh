#!/usr/bin/env bash
# wait_bench.sh [timeout_sec] — bench.sh の走行中（.bench.lock がある間）は待つ。
# ビルド・pytest・大きな解析の前に呼ぶ（方針 §6）。
# 終了コード: 0 = 空いた（または最初から空き）、1 = timeout_sec 待っても空かない、2 = 引数エラー
# ロックの pid が生きていなければ「古いロック」として空き扱いにする（消すのは bench.sh の仕事）。
set -u
timeout="${1:-0}"
case "$timeout" in *[!0-9]*) echo "wait_bench: timeout_sec は整数" >&2; exit 2;; esac
lock="$(cd "$(dirname "$0")" && pwd)/.bench.lock"
waited=0
while [ -e "$lock" ]; do
    pid="$(cut -d' ' -f1 "$lock" 2>/dev/null)"
    if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
        echo "wait_bench: 古いロック（pid ${pid:-?} は居ない）: $(cat "$lock")" >&2
        exit 0
    fi
    if [ "$timeout" -gt 0 ] && [ "$waited" -ge "$timeout" ]; then
        echo "wait_bench: ${timeout}s 待ちましたがまだ走行中: $(cat "$lock")" >&2
        exit 1
    fi
    [ $((waited % 30)) -eq 0 ] && echo "wait_bench: 走行中（${waited}s 待機）: $(cat "$lock")" >&2
    sleep 5; waited=$((waited + 5))
done
exit 0
