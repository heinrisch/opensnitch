#!/usr/bin/env bash
set -euo pipefail

build_dir=${1:?Usage: install-local.sh BUILD_DIR}
project_dir=$(cd "$(dirname "$0")/.." && pwd)
runtime=/opt/opensnitch-local

if [[ $EUID != 0 ]]; then
    echo 'Installation requires root (use make update).' >&2
    exit 1
fi

# Finish installing the UI before touching the running daemon.
python3 -m venv "$runtime"
"$runtime/bin/python" -m pip install --no-index --find-links "$build_dir/wheels" --upgrade --force-reinstall -r "$project_dir/ui/requirements.txt" opensnitch-ui
install -Dm755 "$project_dir/daemon/opensnitchd" /usr/local/bin/opensnitchd.new
mv /usr/local/bin/opensnitchd.new /usr/local/bin/opensnitchd
install -d /etc/opensnitchd/rules /etc/opensnitchd/tasks
for file in default-config.json system-fw.json network_aliases.json; do
    if [[ ! -e /etc/opensnitchd/$file ]]; then
        install -m644 "$project_dir/daemon/data/$file" "/etc/opensnitchd/$file"
    fi
done
if [[ ! -e /etc/opensnitchd/tasks/tasks.json ]]; then
    install -m600 "$project_dir/daemon/data/tasks/tasks.json" /etc/opensnitchd/tasks/tasks.json
fi
if ! systemctl cat opensnitchd.service >/dev/null 2>&1; then
    install -Dm644 "$project_dir/daemon/data/init/opensnitchd.service" /etc/systemd/system/opensnitchd.service
fi
install -d /etc/systemd/system/opensnitchd.service.d
cat > /etc/systemd/system/opensnitchd.service.d/local-build.conf <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/local/bin/opensnitchd
EOF
cat > /usr/local/bin/opensnitch-ui <<'EOF'
#!/bin/sh
exec /opt/opensnitch-local/bin/python /opt/opensnitch-local/bin/opensnitch-ui "$@"
EOF
chmod 755 /usr/local/bin/opensnitch-ui
systemctl daemon-reload
systemctl restart opensnitchd.service
systemctl is-active --quiet opensnitchd.service
