import importlib.util
import logging
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("watchdog", Path(__file__).with_name("wifi-watchdog.py"))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.config = {"interface": "wlan0", "connection_uuid": "test", "max_failures": "10"}
        self.logger = unittest.mock.Mock()

    def test_healthy_resets_without_commands_or_logs(self):
        w.save_count(self.state / "failures", 9)
        with patch.object(w, "health", return_value=(True, "")), patch.object(w, "command") as cmd:
            w.cycle(self.config, self.state, self.logger)
        cmd.assert_not_called()
        self.assertEqual((self.state / "failures").read_text(), "0\n")
        self.assertFalse(self.logger.mock_calls)

    def test_reconnect_success_resets(self):
        w.save_count(self.state / "failures", 9)
        with patch.object(w, "health", side_effect=[(False, "gateway"), (True, "")]), patch.object(w, "command", return_value=(0, "")) as cmd:
            w.cycle(self.config, self.state, self.logger)
        self.assertEqual(cmd.call_count, 2)
        self.assertEqual((self.state / "failures").read_text(), "0\n")

    def test_ten_failed_cycles_then_reboot_and_retry_failed_reboot(self):
        with patch.object(w, "health", return_value=(False, "gateway")), patch.object(w, "command", return_value=(1, "failed")) as cmd:
            for count in range(1, 11):
                w.cycle(self.config, self.state, self.logger)
                self.assertEqual(int((self.state / "failures").read_text()), count)
                reboots = [c for c in cmd.call_args_list if c.args[0] == ["systemctl", "reboot"]]
                self.assertEqual(len(reboots), int(count == 10))
            self.logger.error.assert_called_with("Reboot request failed: %s", "failed")
            w.cycle(self.config, self.state, self.logger)
            self.assertEqual(int((self.state / "failures").read_text()), 10)
            self.assertEqual(cmd.call_args.args[0], ["systemctl", "reboot"])

    def test_health_requires_address_gateway_and_ping(self):
        for responses, expected in [
            ([(0, "30 (disconnected)")], False),
            ([(0, "100 (connected)"), (0, '[{"addr_info": []}]')], False),
            ([(0, "100 (connected)"), (0, '[{"addr_info": [{"scope": "global"}]}]'), (0, '[]')], False),
            ([(0, "100 (connected)"), (0, '[{"addr_info": [{"scope": "global"}]}]'), (0, '[{"gateway": "198.51.100.1"}]'), (0, "")], True),
        ]:
            with self.subTest(responses=responses), patch.object(w, "command", side_effect=responses):
                self.assertEqual(w.health("wlan0")[0], expected)

    def test_command_timeout_and_missing_binary(self):
        for error in [subprocess.TimeoutExpired("nmcli", 1), FileNotFoundError("missing")]:
            with patch.object(w.subprocess, "run", side_effect=error):
                self.assertEqual(w.command(["nmcli"])[0], 124)

    def test_persistent_rotated_logs(self):
        handler = w.DurableHandler(self.state / "events.log", maxBytes=150, backupCount=5)
        self.addCleanup(handler.close)
        logger = logging.Logger("rotation-test")
        logger.addHandler(handler)
        with patch.object(w.os, "fsync", wraps=w.os.fsync) as sync:
            for i in range(30):
                logger.error("Fault %d %s", i, "x" * 80)
            self.assertEqual(sync.call_count, 60)
        self.assertEqual(len(list(self.state.glob("events.log*"))), 6)
        self.assertIn("Fault 29", (self.state / "events.log").read_text())


if __name__ == "__main__":
    unittest.main()
