#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
if [ "$(id -u)" -ne 0 ]; then
    echo 'Run with sudo: sudo ./install.sh' >&2
    exit 1
fi
for tool in python3 nmcli ip ping systemctl; do
    command -v "$tool" >/dev/null
done
python3 -c 'import ast; ast.parse(open("wifi-watchdog.py").read())'
config_path=wifi-watchdog.conf
if [ -e /etc/wifi-watchdog.conf ]; then
    config_path=/etc/wifi-watchdog.conf
fi
python3 - "$config_path" <<'PY'
import configparser
import sys
import uuid

config = configparser.ConfigParser()
config.read(sys.argv[1])
try:
    uuid.UUID(config["watchdog"]["connection_uuid"])
except (KeyError, ValueError):
    sys.exit("Set connection_uuid to your actual Wi-Fi connection UUID in " + sys.argv[1])
PY
install -m 0755 wifi-watchdog.py /usr/local/sbin/wifi-watchdog.py
if [ ! -e /etc/wifi-watchdog.conf ]; then
    install -m 0600 wifi-watchdog.conf /etc/wifi-watchdog.conf
fi
install -m 0644 wifi-watchdog.service wifi-watchdog.timer /etc/systemd/system/
install -d -m 0700 /var/lib/wifi-watchdog
systemd-analyze verify /etc/systemd/system/wifi-watchdog.service /etc/systemd/system/wifi-watchdog.timer
systemctl daemon-reload
systemctl enable --now wifi-watchdog.timer
systemctl status wifi-watchdog.timer --no-pager
