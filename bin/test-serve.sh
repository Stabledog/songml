#!/usr/bin/env bash
# test-serve.sh - start/stop/bounce a dev instance of songml-serve
#
# Usage:
#   test-serve.sh start
#   test-serve.sh stop
#   test-serve.sh bounce
#   test-serve.sh status
#
# The port defaults to 8081 and can be overridden with SONGML_TEST_SERVE_PORT.
# stop/bounce only ever kill the process currently bound to that port, so a
# production instance on a different port (e.g. 8080) is never touched.

set -euo pipefail
#shellcheck disable=2154
PS4='$( _0=$?; exec 2>/dev/null; realpath -- "${BASH_SOURCE[0]:-?}:${LINENO} ^$_0 ${FUNCNAME[0]:-?}()=>" ) '
[[ -n "${DEBUGSH:-}" ]] && set -x

scriptName="${scriptName:-"$(command readlink -f -- "$0")"}"
scriptDir="$(command dirname -- "${scriptName}")"

export SONGML_TEST_SERVE_PORT=${SONGML_TEST_SERVE_PORT:-8081}

die() {
    builtin echo "ERROR($(basename "${scriptName}")): $*" >&2
    builtin exit 1
}

{  # outer scope braces

    usage() {
        cut -c 12- <<'EOF'
            Usage: test-serve.sh {start|stop|bounce|status}

            Starts/stops/bounces a songml-serve instance for local testing.

            Port defaults to 8081; override with SONGML_TEST_SERVE_PORT.
            stop/bounce only kill the process currently listening on that
            port, so other instances (e.g. production on :8080) are safe.
EOF
        exit 2
    }

    pid_on_port() {
        local port="$1"
        ss -ltnp "sport = :${port}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -n1 || true
    }

    do_start() {
        local port="$1"
        local samples_dir="${scriptDir}/../samples"
        local log_file="${TMPDIR:-/tmp}/songml-test-serve-${port}.log"

        local existing_pid
        existing_pid="$(pid_on_port "$port")"
        if [[ -n "$existing_pid" ]]; then
            die "port ${port} is already in use (pid ${existing_pid}), possibly serving ${samples_dir} — run 'stop' first or set SONGML_TEST_SERVE_PORT"
        fi

        [[ -d "$samples_dir" ]] || die "samples dir not found: ${samples_dir}"

        echo "Starting songml-serve on port ${port} (log: ${log_file}) ..."
        songml-serve --root "$samples_dir" --port "$port" --reload >"$log_file" 2>&1 &
        disown

        local tries=0
        while [[ -z "$(pid_on_port "$port")" ]]; do
            tries=$((tries + 1))
            if [[ "$tries" -ge 20 ]]; then
                die "songml-serve did not come up on port ${port}; see ${log_file}"
            fi
            sleep 0.2
        done

        echo "songml-serve running on port ${port} (pid $(pid_on_port "$port")), serving ${samples_dir}"
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
        local samples_dir="${scriptDir}/../samples"
        local pid
        pid="$(pid_on_port "$port")"

        if [[ -n "$pid" ]]; then
            echo "songml-serve running on port ${port} (pid ${pid}), serving ${samples_dir}"
        else
            echo "No server running on port ${port} (would serve ${samples_dir})"
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
