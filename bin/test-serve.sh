#!/usr/bin/env bash
# test-serve.sh - start/stop/bounce/status songml-serve, running THIS dev
# tree's code (via `uv run`) against the real chord-sheet library, replacing
# whatever is currently bound to the port. Since it's `uv run`, --reload's
# file-watcher watches this tree's own source, not an installed copy.
# Usage: test-serve.sh {start|stop|bounce|status}
# Port: SONGML_TEST_SERVE_PORT (default 8080). Root: SONGML_SERVE_ROOT
# (default: the real content mount, falling back to samples/ if absent).

set -euo pipefail
#shellcheck disable=2154
PS4='$( _0=$?; exec 2>/dev/null; realpath -- "${BASH_SOURCE[0]:-?}:${LINENO} ^$_0 ${FUNCNAME[0]:-?}()=>" ) '
[[ -n "${DEBUGSH:-}" ]] && set -x

scriptName="${scriptName:-"$(command readlink -f -- "$0")"}"
scriptDir="$(command dirname -- "${scriptName}")"

export SONGML_TEST_SERVE_PORT=${SONGML_TEST_SERVE_PORT:-8080}

die() {
    builtin echo "ERROR($(basename "${scriptName}")): $*" >&2
    builtin exit 1
}

{  # outer scope braces

    _default_serve_root() {
        local real_root="/host_home/Dropbox/AbletonLive/Sheets"
        if [[ -d "$real_root" ]]; then
            builtin echo "$real_root"
        else
            builtin echo "${scriptDir}/../samples"
        fi
    }

    usage() {
        cut -c 12- <<'EOF'
            Usage: test-serve.sh {start|stop|bounce|status}

            Starts/stops/bounces songml-serve, running this dev tree's code
            (via `uv run`) against the real chord-sheet library.

            Port defaults to 8080; override with SONGML_TEST_SERVE_PORT.
            Root defaults to the real content mount; override with
            SONGML_SERVE_ROOT. stop/bounce only kill the process currently
            listening on the target port, so pointing this at a different
            port leaves any instance elsewhere untouched.
EOF
        exit 2
    }

    pid_on_port() {
        local port="$1"
        ss -ltnp "sport = :${port}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -n1 || true
    }

    do_start() {
        local port="$1"
        local pkg_dir="${scriptDir}/../songml-utils"
        local serve_root="${SONGML_SERVE_ROOT:-$(_default_serve_root)}"
        local log_file="${TMPDIR:-/tmp}/songml-test-serve-${port}.log"

        local existing_pid
        existing_pid="$(pid_on_port "$port")"
        if [[ -n "$existing_pid" ]]; then
            die "port ${port} is already in use (pid ${existing_pid}) — run 'stop' or 'bounce' first, or set SONGML_TEST_SERVE_PORT"
        fi

        [[ -d "$serve_root" ]] || die "serve root not found: ${serve_root}"

        echo "Starting songml-serve (local dev tree) on port ${port} (log: ${log_file}) ..."
        ( builtin cd -- "$pkg_dir" \
          && uv run songml-serve --root "$serve_root" --port "$port" --reload \
        ) >"$log_file" 2>&1 &
        disown

        local tries=0
        while [[ -z "$(pid_on_port "$port")" ]]; do
            tries=$((tries + 1))
            if [[ "$tries" -ge 20 ]]; then
                die "songml-serve did not come up on port ${port}; see ${log_file}"
            fi
            sleep 0.2
        done

        echo "songml-serve running on port ${port} (pid $(pid_on_port "$port")), serving ${serve_root}"
    }

    do_stop() {
        local port="$1"
        local pid
        pid="$(pid_on_port "$port")"

        if [[ -z "$pid" ]]; then
            echo "No server running on port ${port}"
            return 0
        fi

        echo "Stopping songml-serve on port ${port} (pid ${pid}) ..."
        kill "$pid"

        local tries=0
        while [[ -n "$(pid_on_port "$port")" ]]; do
            tries=$((tries + 1))
            if [[ "$tries" -ge 20 ]]; then
                echo "pid ${pid} did not exit; sending SIGKILL" >&2
                kill -9 "$pid" 2>/dev/null || true
                break
            fi
            sleep 0.2
        done
    }

    do_status() {
        local port="$1"
        local serve_root="${SONGML_SERVE_ROOT:-$(_default_serve_root)}"
        local pid
        pid="$(pid_on_port "$port")"

        if [[ -n "$pid" ]]; then
            echo "songml-serve running on port ${port} (pid ${pid})"
        else
            echo "No server running on port ${port} (would serve ${serve_root})"
        fi
    }

}

main() {
    local cmd="${1:-}"
    local port="${SONGML_TEST_SERVE_PORT}"

    case "$cmd" in
        start)
            do_start "$port"
            ;;
        stop)
            do_stop "$port"
            ;;
        bounce|restart)
            do_stop "$port"
            do_start "$port"
            ;;
        status)
            do_status "$port"
            ;;
        *)
            usage
            ;;
    esac
}

if [[ -z "${sourceMe:-}" ]]; then
    main "$@"
    exit
fi
command true
