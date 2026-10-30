#!/usr/bin/python3
"""Check and recover Wi-Fi once; invoked every minute by systemd."""
import configparser
import fcntl
import json
import logging
import logging.handlers
import os
from pathlib import Path
import subprocess
import time


class DurableHandler(logging.handlers.RotatingFileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()
        os.fsync(self.stream.fileno())
        fd = os.open(Path(self.baseFilename).parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def handleError(self, record):
        raise RuntimeError("Cannot persist watchdog log")


def command(args, timeout=1):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                                env={**os.environ, "LC_ALL": "C"})
        return result.returncode, (result.stdout + result.stderr).strip()[:1000]
    except (subprocess.TimeoutExpired, OSError) as error:
        return 124, str(error)[:1000]


def health(interface):
    code, state = command(["nmcli", "-g", "GENERAL.STATE", "device", "show", interface])
    if code or not state.startswith("100 "):
        return False, "wireless disconnected: " + state
    code, address = command(["ip", "-j", "-4", "address", "show", "dev", interface])
    if code:
        return False, "cannot read IPv4: " + address
    if not any(a.get("scope") == "global" for dev in json.loads(address)
               for a in dev.get("addr_info", [])):
        return False, "no IPv4 address"
    code, routes = command(["ip", "-j", "-4", "route", "show", "default", "dev", interface])
    if code:
        return False, "cannot read gateway: " + routes
    gateway = next((r.get("gateway") for r in json.loads(routes) if r.get("gateway")), None)
    if not gateway:
        return False, "no IPv4 gateway"
    code, _ = command(["ping", "-n", "-I", interface, "-c", "3", "-W", "1", gateway], 5)
    return (False, "gateway unreachable: " + gateway) if code else (True, "")


def save_count(path, count):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(str(count) + "\n")
    temporary.replace(path)


def cycle(config, state_dir, logger):
    count_path = state_dir / "failures"
    count = int(count_path.read_text()) if count_path.exists() else 0
    interface = config["interface"]
    limit = int(config["max_failures"])
    healthy, reason = health(interface)
    if healthy:
        save_count(count_path, 0)
        return
    logger.warning("Network fault; attempt %d/%d: %s", min(count + 1, limit), limit, reason)
    # Disconnect failure is expected if the interface is already disconnected.
    command(["nmcli", "--wait", "5", "device", "disconnect", interface], 6)
    code, detail = command(["nmcli", "--wait", "25", "connection", "up", "uuid",
                            config["connection_uuid"], "ifname", interface], 26)
    healthy, reason = health(interface)
    if healthy:
        save_count(count_path, 0)
        return
    count = min(count + 1, limit)
    save_count(count_path, count)
    logger.error("Reconnect failed %d/%d: %s; nmcli status=%d %s",
                 count, limit, reason, code, " ".join(detail.splitlines()))
    if count >= limit:
        logger.critical("Failure limit reached (%d); requesting system reboot", limit)
        code, detail = command(["systemctl", "reboot"], 5)
        if code:
            logger.error("Reboot request failed: %s", detail)


def main():
    os.umask(0o077)
    parser = configparser.ConfigParser()
    if not parser.read("/etc/wifi-watchdog.conf"):
        raise RuntimeError("Missing /etc/wifi-watchdog.conf")
    config = parser["watchdog"]
    if int(config["max_failures"]) < 1 or int(config["boot_grace_seconds"]) < 0:
        raise ValueError("Invalid retry limit or boot grace")
    if float(Path("/proc/uptime").read_text().split()[0]) < int(config["boot_grace_seconds"]):
        return
    state_dir = Path("/run/wifi-watchdog")
    state_dir.mkdir(mode=0o700, exist_ok=True)
    log_dir = Path("/var/lib/wifi-watchdog")
    log_dir.mkdir(mode=0o700, exist_ok=True)
    logger = logging.getLogger("wifi-watchdog")
    logger.setLevel(logging.WARNING)
    handler = DurableHandler(log_dir / "events.log", maxBytes=1024 * 1024, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    with (state_dir / "lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        try:
            cycle(config, state_dir, logger)
        except Exception:
            logger.exception("Watchdog execution error")
            raise


if __name__ == "__main__":
    main()
