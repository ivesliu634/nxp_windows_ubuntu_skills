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

    def test_doctor_unresolved_interfaces_do_not_imply_blank_eeprom(self):
        for vid, pid in ((0x0403, 0x6011), (0x1A86, 0x55E8)):
            with self.subTest(vid=vid, pid=pid):
                groups = self.groups([
                    port(100 + index, "shared", vid=vid, pid=pid)
                    for index in range(2)
                ])
                args = console.build_parser().parse_args(["doctor"])
                output, errors = io.StringIO(), io.StringIO()
                with mock.patch.object(console, "discover_adapter_groups", return_value=groups), \
                     mock.patch.object(console.subprocess, "run", side_effect=AssertionError("unexpected BCU access")), \
                     contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                    self.assertEqual(console.cmd_doctor(args), 1)
                text = output.getvalue() + errors.getvalue()
                self.assertIn("do not infer COM roles or EEPROM contents", text)
                self.assertIn("--device COMn", text)
                self.assertNotIn("bcu eeprom -w", text)
                self.assertNotIn("blank FTDI EEPROM", text)

    def test_doctor_registry_mapping_is_usable_without_writing_eeprom(self):
        ports = [port(100 + index, "5") for index in range(4)]
        registry = {item.device: ("adapter-location", index) for index, item in enumerate(ports)}
        groups = self.groups(ports, registry)
        for board in (None, "imx8mpevk"):
            with self.subTest(board=board):
                arguments = ["doctor"] + (["--board", board] if board else [])
                args = console.build_parser().parse_args(arguments)
                output, errors = io.StringIO(), io.StringIO()
                with mock.patch.object(console, "discover_adapter_groups", return_value=groups), \
                     mock.patch.object(console.subprocess, "run", side_effect=AssertionError("unexpected BCU access")), \
                     contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                    self.assertEqual(console.cmd_doctor(args), 2)
                text = output.getvalue() + errors.getvalue()
                self.assertIn("usable on this host", text)
                self.assertNotIn("has no serial number", text)
                self.assertNotIn("bcu eeprom -w", text)
                self.assertNotIn("writing the FTDI EEPROM is recommended", text)

    def test_doctor_eeprom_readback_stays_separate_from_interface_identity(self):
        groups = self.groups([port(100, "5"), port(101, "5")])
        args = console.build_parser().parse_args([
            "doctor", "--board", "imx93evk14", "--verify-eeprom", "bcu.exe",
        ])
        cases = (
            ("board model is imx93evk14\ndone", 0, "unknown"),
            ("empty response", 0, "unknown"),
            ("Can't auto recognize the board", 0, "unknown"),
            ("default values to FTDI EEPROM successfully", 0, "unknown"),
            ("Invalid EEPROM context", 0, "blank"),
            ("FTDI EEPROM SN: E10092", 0, "written"),
            ("FTDI EEPROM SN: E10092", 1, None),
        )
        for raw, returncode, state in cases:
            with self.subTest(raw=raw, returncode=returncode):
                output, errors = io.StringIO(), io.StringIO()
                completed = SimpleNamespace(stdout=raw, stderr="", returncode=returncode)
                with mock.patch.object(console, "discover_adapter_groups", return_value=groups), \
                     mock.patch.object(console.subprocess, "run", return_value=completed) as read, \
                     contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                    self.assertEqual(console.cmd_doctor(args), 1)
                self.assertEqual(
                    read.call_args.args[0],
                    ["bcu.exe", "eeprom", "-r", "-board=imx93evk14"],
                )
                text = output.getvalue() + errors.getvalue()
                if state is None:
                    self.assertIn("bcu exited with code 1", text)
                    self.assertIn("EEPROM state is unknown", text)
                    self.assertNotIn("bcu eeprom state = written", text)
                else:
                    self.assertIn(f"bcu eeprom state = {state}", text)
                self.assertIn("identity blank", text)
                self.assertNotIn("bcu eeprom -w", text)
                self.assertNotIn("identity is not written", text)

    def test_doctor_eeprom_verification_requires_one_ftdi_adapter(self):
        cases = (
            [port(100 + index, "shared", vid=0x1A86, pid=0x55E8) for index in range(2)],
            [port(100, "first"), port(101, "second")],
        )
        for ports in cases:
            with self.subTest(ports=ports):
                groups = self.groups(ports)
                args = console.build_parser().parse_args([
                    "doctor", "--board", "imx93evk14", "--verify-eeprom", "bcu.exe",
                ])
                output, errors = io.StringIO(), io.StringIO()
                with mock.patch.object(console, "discover_adapter_groups", return_value=groups), \
                     mock.patch.object(console.subprocess, "run", side_effect=AssertionError("unexpected BCU access")), \
                     contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                    self.assertEqual(console.cmd_doctor(args), 1)
                self.assertIn("BCU read not attempted", errors.getvalue())

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
