#!/usr/bin/env bash
# run_queue.sh [--once] [--poll SEC] — queue/ のジョブを直列に消化する（方針 §6）。
#
# ジョブ: aichallenge/research_tools/queue/<ID>.job（1行、# で始まる行は無視）
#   <commit> <label> [<n>] [<duration_sec>] [--explore]
#   例: 4b01c42 T-0001_ay75 3            → commit 4b01c42 を label T-0001_ay75 で 3 回（既定 1 回、290 秒）
#       4b01c42 probe 1 120 --explore     → 120 秒の探索用走行（meta に explore: true）
#   n は 1〜10、duration は 30〜900 秒。commit はブランチ名やタグでもよい（解決した完全な hash をジョブに追記する）。
# 流れ: 最も古い .job を running/ へ → wait_bench.sh → 専用 worktree（../aichallenge-queue）でその commit を checkout
#   → **このリポジトリの bench.sh**（計測器は常に main 側の版）を BENCH_ROOT=worktree で n 回
#   → 結果はこのリポジトリの results/ → ジョブを done/ へ（準備で失敗、または completed が 0 回なら failed/）。
#   ジョブファイルには解決した commit、各回の終了コードと結果ディレクトリ、completed の回数、失敗理由を追記する。
#   同じ ID の記録が done/・failed/ に既にあれば上書きせず <ID>.<日時>.job として残す。
# 多重起動の防止: queue/.run_queue.lock を flock で取る。取れなければ終了コード 1。
#   起動時に running/ に残っていたジョブ（前回の異常終了）は「# reason: orphaned」を付けて failed/ へ。
# 止める: queue/STOP を置く（今の走行の後で止まる）。--once は 1 ジョブ（無ければ即終了。失敗なら終了コード 1）。
# worktree の初回作成時に、このリポジトリの build/・install/（gitignore 対象）をコピーし、AWSIM はハードリンク、
#   .env はシンボリックリンクにする。install/ の中のリンクは /aichallenge/... のコンテナ内絶対パスなので、
#   worktree をマウントすればその src（Python・yaml・csv）を見る。C++・msg・CMake・package.xml・Dockerfile 等の
#   変更はコピーした build/ に反映されないので、コピー元の commit（build/.build_commit = コピー時の main の HEAD。
#   実際にビルドした commit とは限らない）との差にそれらがあればジョブを failed にする。
set -u

once=0; poll=30
while [ $# -gt 0 ]; do
    case "$1" in
        --once) once=1 ;;
        --poll) poll="${2:?}"; shift; case "$poll" in ''|*[!0-9]*|0) echo "--poll は正の整数" >&2; exit 2;; esac ;;
        *) echo "usage: run_queue.sh [--once] [--poll SEC]" >&2; exit 2 ;;
    esac
    shift
done

tools="$(cd "$(dirname "$0")" && pwd)"
main_root="$(cd "$tools/../.." && pwd)"
queue="$tools/queue"
wt="$(cd "$main_root/.." && pwd)/aichallenge-queue"
build_commit_file="aichallenge/workspace/build/.build_commit"
dur_default=290
mkdir -p "$queue/running" "$queue/done" "$queue/failed"
log="$queue/run_queue.log"
say() { echo "$(date --iso-8601=seconds) $*" >&2; }
now() { date --iso-8601=seconds; }

# 多重起動の防止
exec 9> "$queue/.run_queue.lock"
if ! flock -n 9; then echo "run_queue: 既に別の run_queue.sh が動いています（$queue/.run_queue.lock）" >&2; exit 1; fi

# 前回の異常終了で running/ に残ったジョブ
for j in "$queue"/running/*.job; do
    [ -e "$j" ] || continue
    printf '# reason: orphaned（前回の run_queue が途中で止まった） %s\n' "$(now)" >> "$j"
    mv -n "$j" "$queue/failed/" 2>/dev/null || mv "$j" "$queue/failed/$(basename "$j" .job).$(date +%Y%m%d-%H%M%S).job"
    say "running/ に残っていた $(basename "$j") を failed/ へ"
done

move_record() { # move_record <jobfile> <done|failed>
    local dst="$queue/$2/$(basename "$1")"
    if [ -e "$dst" ]; then dst="$queue/$2/$(basename "$1" .job).$(date +%Y%m%d-%H%M%S).job"; fi
    mv "$1" "$dst"
}

prepare_worktree() { # prepare_worktree <commit> → 0 ok / 1 fail（理由は stderr）
    local commit="$1"
    if [ ! -e "$wt/.git" ]; then
        say "worktree を作成: $wt（build/・install/ のコピーと AWSIM のハードリンク、初回のみ）"
        (
            set -e
            git -C "$main_root" worktree add --detach "$wt" "$commit"
            cp -al "$main_root/aichallenge/simulator/AWSIM" "$wt/aichallenge/simulator/AWSIM"
            [ ! -f "$main_root/.env" ] || ln -s "$main_root/.env" "$wt/.env"
            cp -a "$main_root/aichallenge/workspace/build" "$wt/aichallenge/workspace/build"
            cp -a "$main_root/aichallenge/workspace/install" "$wt/aichallenge/workspace/install"
            git -C "$main_root" rev-parse HEAD > "$wt/$build_commit_file"
        ) || { echo "worktree の作成に失敗。片付けます" >&2; git -C "$main_root" worktree remove --force "$wt" 2>/dev/null; return 1; }
    fi
    if [ -n "$(git -C "$wt" status --porcelain)" ]; then
        echo "worktree が dirty: $(git -C "$wt" status --porcelain | head -3 | tr '\n' ' ')" >&2; return 1
    fi
    build_commit="$(cat "$wt/$build_commit_file" 2>/dev/null)" || { echo "$build_commit_file が読めない" >&2; return 1; }
    [ -n "$build_commit" ] || { echo "$build_commit_file が空" >&2; return 1; }
    # 走行中の worktree を checkout しない
    "$tools/wait_bench.sh" 0
    git -C "$wt" checkout -q --detach "$commit" || return 1
    # コピーした build/ に反映されない変更が含まれていないか。src 配下は py/yaml/yml/csv/json/md と launch/ 以外を全て要リビルド扱い
    local needs
    needs="$( { git -C "$wt" diff --name-only "$build_commit" "$commit" -- aichallenge/workspace/src | grep -vE '\.(py|yaml|yml|csv|json|md)$' | grep -v '/launch/';
                git -C "$wt" diff --name-only "$build_commit" "$commit" -- aichallenge/build_autoware.bash aichallenge/workspace/COLCON_IGNORE docker Dockerfile; } 2>/dev/null | sort -u)"
    if [ -n "$needs" ]; then
        echo "要リビルド（build/ は $build_commit のコピー）: $(echo "$needs" | head -5 | tr '\n' ' ')" >&2; return 1
    fi
    return 0
}

run_job() { # run_job <jobfile in running/> → 0 done / 1 failed（理由は stderr の最終行）
    local job="$1" id line commit label n dur explore=0 tok
    id="$(basename "$job" .job)"
    [ -z "$(tail -c1 "$job")" ] || echo >> "$job"   # 末尾改行が無い行に追記して壊さない
    line="$(grep -v '^#' "$job" | grep -m1 .)"
    commit=""; label=""; n=""; dur=""
    set -f
    for tok in $line; do
        case "$tok" in
            --explore) explore=1 ;;
            *) if [ -z "$commit" ]; then commit="$tok"
               elif [ -z "$label" ]; then label="$tok"
               elif [ -z "$n" ]; then n="$tok"
               elif [ -z "$dur" ]; then dur="$tok"
               else set +f; echo "余分なトークン: $tok" >&2; return 1; fi ;;
        esac
    done
    set +f
    n="${n:-1}"; dur="${dur:-$dur_default}"
    case "$n" in ''|*[!0-9]*|0) echo "n が不正: '$n'" >&2; return 1 ;; esac
    [ "$n" -le 10 ] || { echo "n は 10 以下（予算）: $n" >&2; return 1; }
    case "$dur" in ''|*[!0-9]*) echo "duration が不正: '$dur'" >&2; return 1 ;; esac
    { [ "$dur" -ge 30 ] && [ "$dur" -le 900 ]; } || { echo "duration は 30〜900 秒: $dur" >&2; return 1; }
    case "$label" in ''|*[!A-Za-z0-9_.-]*) echo "label が不正: '$label'" >&2; return 1 ;; esac
    git -C "$main_root" cat-file -e "$commit^{commit}" 2>/dev/null || { echo "commit が無い: $commit" >&2; return 1; }
    local full; full="$(git -C "$main_root" rev-parse "$commit^{commit}")"; commit="${full:0:7}"
    echo "# resolved commit=$full label=$label n=$n dur=$dur explore=$explore" >> "$job"
    say "job $id: commit=$commit label=$label n=$n dur=$dur explore=$explore"
    prepare_worktree "$commit" || return 1
    local k=1 rc out tmp completed=0 lock_retry=0 aborted_streak=0
    tmp="$(mktemp)"
    while [ "$k" -le "$n" ]; do
        "$tools/wait_bench.sh" 0
        say "job $id: run $k/$n"
        BENCH_ROOT="$wt" BENCH_RESULTS_DIR="$tools/results" BENCH_EXPLORE="$explore" BENCH_JOB="$id" BENCH_RUN_INDEX="$k" \
            BENCH_DRIVER="run_queue:$$" BENCH_BUILD_COMMIT="$build_commit" \
            "$tools/bench.sh" "$label" "$dur" > "$tmp" 2>&1; rc=$?
        cat "$tmp" >> "$log"
        if { [ "$rc" -eq 3 ] || [ "$rc" -eq 5 ]; } && [ "$lock_retry" -lt 20 ]; then   # ロック競合・他コンテナあり: 同じ回をやり直す
            lock_retry=$((lock_retry + 1)); say "job $id: rc=$rc（ロック競合か他のコンテナ）、待って再試行 ($lock_retry)"; sleep 15; continue
        fi
        out="$(grep -m1 '^RESULT_DIR=' "$tmp")"
        echo "run $k: rc=$rc ${out#RESULT_DIR=}" >> "$job"
        if [ "$rc" -eq 0 ]; then completed=$((completed + 1)); aborted_streak=0; else aborted_streak=$((aborted_streak + 1)); fi
        if [ "$aborted_streak" -ge 2 ]; then echo "2 回続けて completed にならないので打ち切り" >&2; rm -f "$tmp"; return 1; fi
        k=$((k + 1))
        [ -e "$queue/STOP" ] && { say "job $id: STOP を検出、残り $((n - k + 1)) 回は実行しない"; echo "stopped after run $((k - 1))" >> "$job"; break; }
    done
    rm -f "$tmp"
    echo "completed $completed/$n" >> "$job"
    if [ "$completed" -eq 0 ]; then echo "completed した走行が 0 回" >&2; return 1; fi
    return 0
}

errf="$(mktemp)"
trap 'rm -f "$errf"' EXIT
while :; do
    if [ -e "$queue/STOP" ]; then say "STOP があるので終了"; exit 0; fi
    job="$(ls -tr "$queue"/*.job 2>/dev/null | head -1)"
    if [ -z "$job" ]; then
        [ "$once" = 1 ] && { say "ジョブ無し"; exit 0; }
        sleep "$poll"; continue
    fi
    running="$queue/running/$(basename "$job")"
    [ -z "$(tail -c1 "$job")" ] || echo >> "$job"
    mv "$job" "$running" || exit 1
    echo "# started $(now) by run_queue.sh pid $$" >> "$running"
    if run_job "$running" 2> "$errf"; then
        cat "$errf" | tee -a "$log" >&2
        echo "# done $(now)" >> "$running"
        move_record "$running" done; say "job $(basename "$running" .job): done" | tee -a "$log"
        failed=0
    else
        cat "$errf" | tee -a "$log" >&2
        printf '# reason: %s\n# failed %s\n' "$(grep -v '^20[0-9][0-9]-' "$errf" | tail -1)" "$(now)" >> "$running"
        move_record "$running" failed; say "job $(basename "$running" .job): failed" | tee -a "$log"
        failed=1
    fi
    [ "$once" = 1 ] && exit "$failed"
done
