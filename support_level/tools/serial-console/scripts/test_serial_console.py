import contextlib
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "serial_console", Path(__file__).with_name("serial_console.py")
)
assert SPEC is not None and SPEC.loader is not None
console = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(console)


def port(number, serial_number, *, vid=0x0403, pid=0x6011, location=None):
    return SimpleNamespace(
        device=f"COM{number}", serial_number=serial_number, vid=vid, pid=pid,
        location=location, description="mock adapter",
    )


class SerialConsoleTests(unittest.TestCase):
    def setUp(self):
        for target, name, options in (
            (console, "windows_ftdi_registry_map", {"return_value": {}}),
            (console.list_ports, "comports", {"return_value": []}),
            (console.serial, "Serial", {"side_effect": AssertionError("hardware access disabled")}),
        ):
            patcher = mock.patch.object(target, name, **options)
            patcher.start()
            self.addCleanup(patcher.stop)

    def groups(self, ports, registry=None):
        with mock.patch.object(console.list_ports, "comports", return_value=ports), \
             mock.patch.object(console, "windows_ftdi_registry_map", return_value=registry or {}):
            return console.discover_adapter_groups()

    def test_ftdi_letters_keep_fixed_interface_order(self):
        group = self.groups([port(100 + index, f"ABC{letter}") for index, letter in enumerate("ABCD")])[0]
        self.assertEqual([item["interface"] for item in group["interfaces"]], ["if00", "if01", "if02", "if03"])

    def test_shared_ftdi_serial_uses_registry(self):
        ports = [port(100 + index, "5") for index in range(4)]
        registry = {item.device: ("adapter-location", index) for index, item in enumerate(ports)}
        group = self.groups(ports, registry)[0]
        self.assertEqual([item["interface"] for item in group["interfaces"]], ["if00", "if01", "if02", "if03"])
        self.assertEqual(console.adapter_identity_health(group)["status"], "degraded")

    def test_ch9114_missing_first_port_does_not_shift_roles(self):
        group = self.groups([
            port(100 + index, "shared", vid=0x1A86, pid=0x55E8, location=f"1-4:x.{index * 2}")
            for index in (1, 2, 3)
        ])[0]
        self.assertEqual([item["interface"] for item in group["interfaces"]], ["if01", "if02", "if03"])
        with self.assertRaisesRegex(SystemExit, "not present"):
            console.resolve_device({"ports": {"linux": {"interface": "if00"}}}, "linux", None, group=group, require_present=True)

    def test_single_remaining_ch9114_port_keeps_identity(self):
        group = self.groups([port(102, "shared", vid=0x1A86, pid=0x55E8, location="1-4:x.4")])[0]
        self.assertEqual(group["interfaces"][0]["interface"], "if02")

    def test_unresolved_ftdi_does_not_allow_role_selection(self):
        group = self.groups([port(100, "5"), port(101, "5")])[0]
        with self.assertRaisesRegex(SystemExit, "ambiguous"):
            console.resolve_device({"ports": {"linux": {"interface": "if00"}}}, "linux", None, group=group)

    def test_raw_capture_does_not_require_board_or_discovery(self):
        args = console.build_parser().parse_args(["capture", "--device", "COM12"])
        result = {"role": "explicit-device", "state": "done", "bytes": 0, "reconnects": 0, "status": 0}
        with mock.patch.object(console, "load_profile", side_effect=AssertionError("unexpected profile")), \
             mock.patch.object(console, "discover_adapter_groups", side_effect=AssertionError("unexpected discovery")), \
             mock.patch.object(console, "capture_role_loop", return_value=result) as capture, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(console.cmd_capture(args), 0)
        self.assertEqual(capture.call_args.kwargs["device"], "COM12")

    def test_role_capture_without_board_reports_error(self):
        args = console.build_parser().parse_args(["capture", "--role", "a-core"])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(console.cmd_capture(args), 1)

    def test_943_defaults_preserve_bcu_port(self):
        profile = console.load_profile("imx943evk19b1")
        self.assertEqual(console.default_capture_roles(profile), ["cm33s", "a-core", "sm"])
        self.assertEqual(profile["ports"]["cm33s"]["interface"], "if00")
        self.assertFalse(profile["ports"]["second-com"]["default_capture"])


if __name__ == "__main__":
    unittest.main()
