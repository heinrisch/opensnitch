#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID == 0 ]]; then
    echo 'Run make update as your desktop user, without sudo.' >&2
    exit 1
fi
if [[ -z ${DISPLAY:-}${WAYLAND_DISPLAY:-} ]]; then
    echo 'Run this target from your graphical desktop session to restart the UI.' >&2
    exit 1
fi
if [[ ${1:-} == --check ]]; then exit 0; fi
# Match only this user's OpenSnitch UI, including Python-launched instances.
mapfile -t ui_pids < <(pgrep -u "$(id -u)" -f '(^|/|[[:space:]])opensnitch-ui([[:space:]]|$)' || true)
if ((${#ui_pids[@]})); then
    kill "${ui_pids[@]}"
    for attempt in {1..50}; do
        running=false
        for pid in "${ui_pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then running=true; fi
        done
        if [[ $running == false ]]; then break; fi
        sleep 0.1
    done
    if [[ $running == true ]]; then
        echo 'The old UI did not stop; close it before running make restart-local.' >&2
        exit 1
    fi
fi
log_dir=${XDG_STATE_HOME:-$HOME/.local/state}/opensnitch
mkdir -p "$log_dir"
nohup /usr/local/bin/opensnitch-ui "$@" >"$log_dir/ui.log" 2>&1 </dev/null &
ui_pid=$!
sleep 2
if ! kill -0 "$ui_pid" 2>/dev/null; then
    echo "UI failed to start. See $log_dir/ui.log" >&2
    exit 1
fi
echo "Updated UI running (PID $ui_pid); log: $log_dir/ui.log"
