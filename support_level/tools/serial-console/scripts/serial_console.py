#!/usr/bin/env python3
"""Windows-native serial console wrapper for i.MX lab boards.

This is a Windows port of the Linux serial-console tool. It keeps the same
command surface (list, probe, prepare, capture, capture-set, send,
uboot-stop, shell, recover), the same board profile concept, the same
session summary and exit-code contract. Only the platform-specific layers
are reimplemented:

  - device discovery: uses pyserial list_ports instead of Linux sysfs and
    /dev/serial/by-id. On Windows the stable per-interface identity comes
    from the FTDI serial number trailing letter (A -> if00, B -> if01, ...).
  - interactive shell: uses msvcrt on Windows instead of termios/tty.
  - prepare: pyserial configures the framing on open, so this only verifies
    that every role can be opened. There is no stty on Windows.
  - recover: Windows has no sysfs driver bind. This reports the missing
    interfaces and asks the operator to re-enumerate the adapter.

Requires: pyserial, PyYAML.
"""
from __future__ import annotations

import argparse
import codecs
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time
from typing import Any

import serial
from serial.tools import list_ports
import yaml


TOOL_ROOT = Path(__file__).resolve().parent
PROFILE_ROOT = TOOL_ROOT / "profiles"
PROFILE_STATES = {"verified", "partial", "unknown"}

IS_WINDOWS = os.name == "nt"

# Optional interactive backends. On Windows we use msvcrt; on POSIX we fall
# back to termios/tty so the same script still works when copied to Linux.
try:  # pragma: no cover - platform dependent
    import msvcrt  # type: ignore
except ImportError:  # pragma: no cover
    msvcrt = None  # type: ignore

try:  # pragma: no cover - platform dependent
    import termios  # type: ignore
    import tty  # type: ignore
    import select  # type: ignore
except ImportError:  # pragma: no cover
    termios = None  # type: ignore
    tty = None  # type: ignore
    select = None  # type: ignore

# Windows registry access, used only as a fallback to recover the interface
# order of FT4232H adapters whose EEPROM has no serial number (see
# windows_ftdi_registry_map). Absent on POSIX.
try:  # pragma: no cover - platform dependent
    import winreg  # type: ignore
except ImportError:  # pragma: no cover
    winreg = None  # type: ignore



# ---------------------------------------------------------------------------
# Profile loading and validation
# ---------------------------------------------------------------------------
def load_profile(board: str) -> dict[str, Any]:
    path = PROFILE_ROOT / board / "serial.yaml"
    if not path.is_file():
        raise SystemExit(f"serial profile not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"invalid serial profile: {path}")
    validate_profile(data, path)
    return data


def validate_profile(profile: dict[str, Any], path: Path | None = None) -> None:
    label = str(path or "<profile>")
    schema_version = int(profile.get("schema_version") or 1)
    if schema_version not in {1, 2, 3}:
        raise SystemExit(f"unsupported serial profile schema {schema_version}: {label}")

    state = str(profile.get("profile_status") or "unknown")
    if state not in PROFILE_STATES:
        raise SystemExit(f"invalid profile_status '{state}': {label}")

    ports = profile.get("ports") or {}
    if not isinstance(ports, dict):
        raise SystemExit(f"serial profile field 'ports' must be a mapping: {label}")

    seen_orders: dict[int, str] = {}
    seen_interfaces: dict[str, str] = {}
    for role, raw_entry in ports.items():
        if not isinstance(raw_entry, dict):
            raise SystemExit(f"serial role '{role}' must be a mapping: {label}")
        order = raw_entry.get("order")
        if order is not None:
            order = int(order)
            if order < 1:
                raise SystemExit(f"serial role '{role}' has invalid order {order}: {label}")
            if order in seen_orders:
                raise SystemExit(
                    f"serial roles '{seen_orders[order]}' and '{role}' share order {order}: {label}"
                )
            seen_orders[order] = str(role)
        interface = normalize_interface(raw_entry.get("interface"))
        if raw_entry.get("interface") is not None and not interface:
            raise SystemExit(
                f"serial role '{role}' has invalid interface "
                f"'{raw_entry.get('interface')}': {label}"
            )
        if interface:
            if interface in seen_interfaces:
                raise SystemExit(
                    f"serial roles '{seen_interfaces[interface]}' and '{role}' share interface "
                    f"{interface}: {label}"
                )
            seen_interfaces[interface] = str(role)
        if order is not None and interface and int(interface[2:], 16) + 1 != order:
            raise SystemExit(
                f"serial role '{role}' order {order} does not match interface "
                f"{interface}: {label}"
            )
        port_state = str(raw_entry.get("status") or "unknown")
        if port_state not in PROFILE_STATES:
            raise SystemExit(
                f"serial role '{role}' has invalid status '{port_state}': {label}"
            )


def normalize_interface(value: Any) -> str:
    if value is None:
        return ""
    match = re.fullmatch(r"(?:if)?([0-9a-fA-F]{1,2})", str(value).strip())
    if not match:
        return ""
    return f"if{int(match.group(1), 16):02d}"


def get_ports(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ports = profile.get("ports") or {}
    if not isinstance(ports, dict):
        raise SystemExit("serial profile field 'ports' must be a mapping")
    return ports


def adapter_spec(profile: dict[str, Any]) -> dict[str, Any]:
    raw = profile.get("adapter") or {}
    if isinstance(raw, dict):
        return raw
    return {"name": str(raw)}


def port_interface(entry: dict[str, Any]) -> str:
    interface = normalize_interface(entry.get("interface"))
    if interface:
        return interface
    order = entry.get("order")
    if order is not None:
        return f"if{int(order) - 1:02d}"
    return ""


# ---------------------------------------------------------------------------
# Windows device discovery
#
# pyserial on Windows does not populate location or interface, but FTDI
# multi-port adapters append a trailing letter to the USB serial number
# (A/B/C/D for a quad FT4232H). The base serial identifies the physical
# adapter; the trailing letter identifies the interface (A -> if00).
# ---------------------------------------------------------------------------
def usb_id_from_port(port: Any) -> str:
    if port.vid is None or port.pid is None:
        return ""
    return f"{port.vid:04x}:{port.pid:04x}"


def split_serial(serial_number: str | None) -> tuple[str, str | None]:
    """Return (base_serial, interface_letter) for an FTDI-style serial.

    A trailing uppercase letter is treated as the interface selector. If the
    serial has no such letter, the whole string is the base and the letter is
    None (single-interface adapter).
    """
    if not serial_number:
        return "", None
    text = str(serial_number)
    if len(text) > 1 and text[-1].isalpha() and text[-1].isupper():
        return text[:-1], text[-1]
    return text, None


def parse_location_index(location: Any) -> int | None:
    """Return an integer ordering hint from a USB location string, or None.

    pyserial reports a per-interface USB location such as "1-4:x.0" / "1-4:x.2"
    for a shared-serial multi-interface bridge (e.g. WCH CH9114). The number
    after the final "." orders the interfaces on the device. We return that
    raw number; the caller uses the bridge's fixed endpoint layout, never
    the rank of the currently visible ports.
    """
    if not location:
        return None
    tail = str(location).rsplit('.', 1)[-1]
    digits = ''.join(ch for ch in tail if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def windows_ftdi_registry_map() -> dict[str, tuple[str, int]]:
    """Map COM name -> (adapter_location_key, interface_index) from the registry.

    FT4232H adapters whose EEPROM has no serial number do not expose the
    A/B/C/D trailing letter that split_serial relies on: pyserial then reports
    the same bare serial (for example "5") for all four interfaces, so every
    interface collapses onto if00. Windows still keeps a stable per-interface
    identity in the device instance path under
    HKLM\\SYSTEM\\CurrentControlSet\\Enum\\FTDIBUS, for example
    "VID_0403+PID_6011+5&2630a0c1&0&4&3". The tail "&3" is the 1-based
    interface index and the remaining location ("5&2630a0c1&0&4") is stable per
    physical adapter. This recovers the real order for those adapters.

    Returns an empty map on non-Windows hosts or when winreg is unavailable.
    Adapters that do expose a real serial number (instance id has no "&") are
    skipped so the normal trailing-letter path keeps handling them.
    """
    if not IS_WINDOWS or winreg is None:
        return {}
    mapping: dict[str, tuple[str, int]] = {}
    base_path = r"SYSTEM\CurrentControlSet\Enum\FTDIBUS"
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path)
    except OSError:
        return {}
    try:
        index = 0
        while True:
            try:
                instance = winreg.EnumKey(root, index)
            except OSError:
                break
            index += 1
            # Instance id looks like VID_0403+PID_6011+<serial-or-location>.
            tail = instance.split("+")[-1]
            if "&" not in tail:
                # Real EEPROM serial (e.g. 0C1819A); handled by split_serial.
                continue
            parts = tail.split("&")
            try:
                iface_index = int(parts[-1]) - 1
            except ValueError:
                continue
            location_key = "&".join(parts[:-1])
            try:
                inst_key = winreg.OpenKey(root, instance)
            except OSError:
                continue
            try:
                sub = 0
                while True:
                    try:
                        child = winreg.EnumKey(inst_key, sub)
                    except OSError:
                        break
                    sub += 1
                    try:
                        params = winreg.OpenKey(
                            inst_key, child + r"\Device Parameters"
                        )
                    except OSError:
                        continue
                    try:
                        port_name, _ = winreg.QueryValueEx(params, "PortName")
                    except OSError:
                        continue
                    finally:
                        params.Close()
                    if port_name:
                        mapping[str(port_name)] = (location_key, iface_index)
            finally:
                inst_key.Close()
    finally:
        root.Close()
    return mapping


def is_usb_serial(port: Any) -> bool:
    return port.vid is not None and port.pid is not None


def discover_serial_interfaces() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    registry_map = windows_ftdi_registry_map()
    ports = [p for p in list_ports.comports() if is_usb_serial(p)]
    # Registry identity takes precedence over shared or missing serial numbers.
    # CH9114 uses fixed USB endpoints even when only one interface is visible.
    serial_counts: dict[str, int] = {}
    for port in ports:
        key = port.serial_number or ""
        serial_counts[key] = serial_counts.get(key, 0) + 1
    for port in ports:
        serial_number = port.serial_number or ""
        shared_serial = (
            usb_id_from_port(port) == "1a86:55e8"
            or bool(serial_number) and serial_counts.get(serial_number, 0) > 1
        )
        reg_index: int | None = None
        loc_index: int | None = None
        entry = registry_map.get(str(port.device))
        if entry is not None:
            base, reg_index = entry
            letter = None
            id_source = "registry"
        elif shared_serial:
            # Shared serial across interfaces: keep the whole serial as the
            # adapter base and separate interfaces by USB location, never by a
            # trailing letter (the last character belongs to the serial itself).
            base = serial_number or str(port.location or port.device).rsplit(".", 1)[0]
            letter = None
            loc_index = parse_location_index(port.location)
            id_source = "usb-location" if usb_id_from_port(port) == "1a86:55e8" else "ambiguous"
        else:
            base, letter = split_serial(port.serial_number)
            if letter is not None:
                id_source = "ftdi-letter"
            else:
                id_source = "ambiguous" if usb_id_from_port(port) == "0403:6011" else "single"
        records.append(
            {
                "device": port.device,
                "usb_id": usb_id_from_port(port),
                "serial_number": serial_number,
                "base_serial": base,
                "letter": letter,
                "reg_index": reg_index,
                "loc_index": loc_index,
                "id_source": id_source,
                "product": port.description or "",
            }
        )
    return records



def group_serial_interfaces(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        base = record["base_serial"] or record["device"]
        key = (record["usb_id"], base)
        group = grouped.setdefault(
            key,
            {
                "key": base,
                "serial": base,
                "usb_id": record["usb_id"],
                "product": record["product"],
                "interfaces": [],
                "_records": [],
            },
        )
        group["_records"].append(record)

    result = []
    for group in grouped.values():
        recs = group.pop("_records")
        for record in recs:
            letter = record["letter"]
            reg_index = record.get("reg_index")
            if letter is not None:
                index = ord(letter.upper()) - ord("A")
            elif reg_index is not None:
                # Adapter has no EEPROM serial letter; use the interface order
                # recovered from the Windows device instance path.
                index = int(reg_index)
            elif (
                group["usb_id"] == "1a86:55e8"
                and record.get("loc_index") in {0, 2, 4, 6}
            ):
                index = record["loc_index"] // 2
            else:
                index = 0
                if record.get("id_source") != "single":
                    record["id_source"] = "ambiguous"
            interface = f"if{index:02d}"
            group["interfaces"].append(
                {
                    "device": record["device"],
                    "interface": interface,
                    "order": index + 1,
                    "serial_number": record["serial_number"],
                    "letter": letter,
                    "id_source": record.get("id_source"),
                }
            )
        group["interfaces"].sort(key=lambda item: (item["order"], item["device"]))
        result.append(group)
    return sorted(result, key=lambda item: item["key"])


def discover_adapter_groups() -> list[dict[str, Any]]:
    return group_serial_interfaces(discover_serial_interfaces())


# ---------------------------------------------------------------------------
# Board-agnostic adapter identity health
# Interface identity alone does not establish EEPROM contents or writability.
# ---------------------------------------------------------------------------
def adapter_identity_health(group: dict[str, Any]) -> dict[str, Any]:
    """Classify how usable an adapter's per-interface identity is.

    Returns a dict with keys:
      status  - one of "ok", "degraded", "blank".
                ok       every interface has a stable identity (FTDI trailing
                         letter, or the adapter has a single interface).
                degraded interface order was recovered from the Windows
                         registry fallback. Usable on this host.
                blank    interface identities cannot be distinguished. This
                         legacy status name is not an EEPROM diagnosis.
      summary - short human-readable explanation.
      serial  - the base serial reported by the adapter (may be a bare number).
    """
    interfaces = group.get("interfaces") or []
    serial = str(group.get("serial") or group.get("key") or "")
    if any(item.get("id_source") == "ambiguous" for item in interfaces):
        return {
            "status": "blank",
            "summary": "interface identity is unresolved; do not infer COM roles or EEPROM contents",
            "serial": serial,
        }
    if len(interfaces) <= 1:
        return {"status": "ok", "summary": "single interface", "serial": serial}
    if any(item.get("letter") is not None for item in interfaces):
        return {
            "status": "ok",
            "summary": "per-interface FTDI serial letters present",
            "serial": serial,
        }
    distinct = {item.get("interface") for item in interfaces}
    if interfaces and all(
        item.get("id_source") == "usb-location" for item in interfaces
    ) and len(distinct) == len(interfaces):
        # Shared-serial bridge (e.g. CH9114): interfaces are separated by USB
        # location, not by an FTDI trailing letter. Distinct locations mean the
        # identity is stable and usable, so this is healthy, not degraded.
        return {
            "status": "ok",
            "summary": (
                "per-interface identity from USB location (shared-serial bridge)"
            ),
            "serial": serial,
        }
    if len(distinct) < len(interfaces):
        return {
            "status": "blank",
            "summary": (
                f"{len(interfaces)} interfaces share an interface identity; "
                "EEPROM contents cannot be inferred"
            ),
            "serial": serial,
        }
    return {
        "status": "degraded",
        "summary": (
            "interface order recovered from the Windows registry fallback; "
            "EEPROM contents cannot be inferred"
        ),
        "serial": serial,
    }


def classify_bcu_eeprom_output(text: str) -> dict[str, Any]:
    """Interpret the text output of "bcu eeprom -r" without being fooled by echo.

    bcu prints a line "board model is <name>" that merely ECHOES the value
    passed to its -board= option; it is NOT read from the board. Passing a
    wrong model still echoes that wrong model, so this line must never be
    treated as a confirmed identity. This helper looks past that echo at the
    lines that actually reflect the FTDI EEPROM state and returns:

      state       - "blank"   BCU reported an invalid EEPROM context; chip
                             presence and writability remain unproven,
                    "written" a real identity was read back,
                    "unknown" output did not match either pattern.
      echoed_board- the model echoed from -board=, kept only so callers can
                    warn that it is an echo, never as a verified identity.
      detail      - short human-readable explanation.

    This encodes the lesson from the imx8mpevk bring-up so neither a human nor
    the tool mistakes the echoed model line for a successful identity read.
    """
    echoed = None
    match = re.search(r"board model is\s+(\S+)", text)
    if match:
        echoed = match.group(1)
    lowered = text.lower()
    blank_markers = (
        "invalid eeprom context",
    )
    written_markers = (
        "ftdi eeprom sn",
    )
    if any(marker in lowered for marker in blank_markers):
        return {
            "state": "blank",
            "echoed_board": echoed,
            "detail": (
                "BCU reported an invalid EEPROM context; this does not prove "
                "chip presence or writability, and the echoed board model "
                "does not confirm identity"
            ),
        }
    if any(marker in lowered for marker in written_markers):
        return {
            "state": "written",
            "echoed_board": echoed,
            "detail": "FTDI EEPROM holds a real identity (SN/Board/SoC read back)",
        }
    return {
        "state": "unknown",
        "echoed_board": echoed,
        "detail": "could not classify bcu eeprom output",
    }


def verify_eeprom_with_bcu(bcu: str, board: str) -> dict[str, Any]:
    """Run "bcu eeprom -r -board=<board>" and classify the real EEPROM state.

    This turns the classify_bcu_eeprom_output rule into an executable check so
    doctor can confirm on real hardware whether the FTDI EEPROM actually holds
    an identity, instead of trusting the "board model is <name>" echo. The
    board name is only used as the -board= argument; the returned "state" comes
    from the EEPROM-context lines, never from that echo.

    Returns the classify_bcu_eeprom_output dict plus keys:
      ran   - True if bcu executed (even if it returned non-zero).
      error - populated when bcu could not complete the read successfully.
      raw   - the combined stdout/stderr text, for logging.
    """
    try:
        completed = subprocess.run(
            [bcu, "eeprom", "-r", f"-board={board}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "ran": False,
            "error": str(exc),
            "state": "unknown",
            "echoed_board": None,
            "detail": "bcu could not be launched",
            "raw": "",
        }
    raw = (completed.stdout or "") + (completed.stderr or "")
    result = classify_bcu_eeprom_output(raw)
    result["ran"] = True
    result["error"] = ""
    result["raw"] = raw
    if completed.returncode != 0:
        result["state"] = "unknown"
        result["error"] = f"bcu exited with code {completed.returncode}"
        result["detail"] = "BCU read failed; EEPROM state is unknown"
    return result


def report_adapter_health(groups: list[dict[str, Any]]) -> str:
    """Print an identity-health line for each adapter and return the worst status.

    This is the shared entry point used by list, probe and doctor so every
    board follows the same identity-check and remediation flow.
    """
    worst = "ok"
    severity = {"ok": 0, "degraded": 1, "blank": 2}
    for index, group in enumerate(groups, 1):
        health = adapter_identity_health(group)
        status = health["status"]
        if severity[status] > severity[worst]:
            worst = status
        if status == "ok":
            continue
        print(
            f"adapter [{index}] id={health['serial']}: identity {status} "
            f"- {health['summary']}"
        )
        if status == "degraded":
            print(
                "  remediation: interface mapping is usable on this host; "
                "this result does not require an EEPROM write"
            )
        else:
            print(
                "  remediation: inspect USB/driver enumeration or capture only "
                "an independently identified --device COMn; do not infer "
                "EEPROM contents or write defaults from this result"
            )
    return worst



def interface_map(group: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not group:
        return {}
    return {str(item["interface"]): item for item in group["interfaces"]}


def group_matches_profile(group: dict[str, Any], profile: dict[str, Any]) -> tuple[bool, int]:
    spec = adapter_spec(profile)
    expected_usb_id = str(spec.get("usb_id") or "").lower()
    if expected_usb_id and str(group.get("usb_id") or "").lower() != expected_usb_id:
        return False, 0

    actual_interfaces = {item["interface"] for item in group["interfaces"]}
    known_interfaces = {
        port_interface(entry)
        for entry in get_ports(profile).values()
        if port_interface(entry)
    }

    score = len(known_interfaces & actual_interfaces) * 10
    score -= len(known_interfaces - actual_interfaces) * 10
    expected_count = spec.get("interface_count")
    if expected_count is not None and len(group["interfaces"]) == int(expected_count):
        score += 5
    if expected_usb_id:
        score += 20
    return True, score


def select_adapter_group(
    groups: list[dict[str, Any]],
    profile: dict[str, Any] | None,
    selector: str | None,
) -> tuple[dict[str, Any] | None, str]:
    candidates = groups
    if selector:
        candidates = [
            group
            for group in groups
            if selector
            in {
                str(group.get("key") or ""),
                str(group.get("serial") or ""),
                str(group.get("usb_id") or ""),
            }
        ]
        if not candidates:
            return None, f"adapter selector did not match: {selector}"

    if profile:
        scored = []
        for group in candidates:
            matches, score = group_matches_profile(group, profile)
            if matches:
                scored.append((score, group))
        if not scored:
            return None, "no detected adapter matches the board profile"
        best_score = max(score for score, _ in scored)
        best = [group for score, group in scored if score == best_score]
        if len(best) != 1:
            return None, "multiple adapters match the board profile; pass --adapter"
        return best[0], ""

    if len(candidates) == 1:
        return candidates[0], ""
    if not candidates:
        return None, "no USB serial adapter detected"
    return None, "multiple serial adapters detected; pass --adapter"


def build_discovery_profile(group: dict[str, Any]) -> dict[str, Any]:
    ports: dict[str, dict[str, Any]] = {}
    for item in group["interfaces"]:
        role = f"port{int(item['order'])}"
        ports[role] = {
            "order": int(item["order"]),
            "interface": item["interface"],
            "device": item["device"],
            "description": "Discovered port; role is not known",
            "default_capture": True,
            "required": True,
            "status": "unknown",
        }
    return {
        "schema_version": 3,
        "board": "unclassified",
        "profile_status": "unknown",
        "adapter": {
            "name": group.get("product") or "discovered USB serial adapter",
            "usb_id": group.get("usb_id") or "",
            "interface_count": len(group["interfaces"]),
        },
        "baudrate": 115200,
        "format": "8N1",
        "ports": ports,
    }


def default_capture_roles(profile: dict[str, Any]) -> list[str]:
    ports = get_ports(profile)
    explicit = [
        str(role)
        for role, entry in ports.items()
        if bool(entry.get("default_capture"))
    ]
    if explicit:
        return sorted(explicit, key=lambda role: int(ports[role].get("order") or 999))

    configured = profile.get("default_capture_roles")
    if isinstance(configured, list) and configured:
        return [str(role) for role in configured if str(role) in ports]

    preferred = [role for role in ("m4", "m33", "a-core", "linux", "scfw") if role in ports]
    if preferred:
        return preferred
    return [
        role
        for role, entry in sorted(
            ports.items(),
            key=lambda item: int(item[1].get("order") or 999),
        )
        if role != "first-com"
    ]


def resolve_device(
    profile: dict[str, Any],
    role: str | None,
    device: str | None,
    *,
    group: dict[str, Any] | None = None,
    require_present: bool = False,
) -> str:
    if device:
        if require_present and not any(
            p.device == device for p in list_ports.comports()
        ):
            raise SystemExit(f"serial device not present: {device}")
        return device
    if not role:
        raise SystemExit("pass --role or --device")
    ports = get_ports(profile)
    if role not in ports:
        known = ", ".join(sorted(ports)) or "<none>"
        raise SystemExit(f"unknown role '{role}'. known roles: {known}")

    entry = ports[role] or {}
    if group is None:
        detected_groups = discover_adapter_groups()
        group, _ = select_adapter_group(detected_groups, profile, None)
    if group is not None and adapter_identity_health(group)["status"] == "blank":
        raise SystemExit("serial interface identity is ambiguous; use --device for raw capture")
    interface = port_interface(entry)
    detected = interface_map(group).get(interface)
    if detected:
        return str(detected["device"])

    if require_present:
        expected = interface or "<unmapped>"
        raise SystemExit(f"serial role '{role}' is not present; expected {expected}")
    raise SystemExit(f"role '{role}' has no detected interface mapping ({interface or '?'})")


def profile_baud(profile: dict[str, Any], baud: int | None) -> int:
    return int(baud or profile.get("baudrate") or 115200)


def probe_profile(
    profile: dict[str, Any],
    group: dict[str, Any] | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "profile_status": str(profile.get("profile_status") or "unknown"),
        "adapter": group,
        "ports": [],
        "errors": [],
        "warnings": [],
    }
    if group is None:
        result["errors"].append("no matching serial adapter")
        for role, entry in get_ports(profile).items():
            result["ports"].append(
                {
                    "role": role,
                    "order": entry.get("order"),
                    "interface": port_interface(entry),
                    "device": "",
                    "present": False,
                    "required": bool(entry.get("required")),
                    "status": str(entry.get("status") or "unknown"),
                }
            )
        return result

    spec = adapter_spec(profile)
    expected_count = spec.get("interface_count")
    actual_count = len(group["interfaces"])
    if expected_count is not None and actual_count != int(expected_count):
        result["errors"].append(
            f"adapter interface count mismatch: expected {expected_count}, detected {actual_count}; "
            "wait for enumeration, replug the adapter, then re-probe"
        )

    detected = interface_map(group)
    for role, entry in get_ports(profile).items():
        interface = port_interface(entry)
        actual = detected.get(interface)
        required = bool(entry.get("required"))
        row = {
            "role": role,
            "order": entry.get("order"),
            "interface": interface,
            "device": actual.get("device", "") if actual else "",
            "present": bool(actual),
            "required": required,
            "default_capture": bool(entry.get("default_capture")),
            "status": str(entry.get("status") or "unknown"),
            "log_sources": entry.get("log_sources") or [],
        }
        result["ports"].append(row)
        if required and not actual:
            result["errors"].append(f"required role '{role}' is missing ({interface or 'unmapped'})")
        elif not actual:
            result["warnings"].append(f"known role '{role}' is not present")

    if result["profile_status"] != "verified":
        result["warnings"].append(
            f"profile is {result['profile_status']}; unmapped interfaces must not be assigned a role"
        )
    return result


# ---------------------------------------------------------------------------
# Serial IO helpers
# ---------------------------------------------------------------------------
def open_serial(device: str, baud: int, timeout: float | None) -> serial.Serial:
    return serial.Serial(
        port=device,
        baudrate=baud,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=timeout,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    )


def append_log(log_path: str | None, data: bytes) -> None:
    if not log_path or not data:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(data)


def emit(data: bytes) -> None:
    if not data:
        return
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def decode_escapes(text: str) -> bytes:
    """Interpret CLI backslash escapes (\\r, \\n, \\t, \\x03) into raw bytes.

    CLI arguments arrive as literal text, so "\\n" is two characters, not a
    newline. Serial line endings and interrupt keys must be sent as the real
    control bytes, so this expands the common escape sequences before writing.
    """
    return codecs.decode(text, "unicode_escape").encode("latin-1")


def touch_log(log_path: str | None) -> None:
    if not log_path:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)


def capture_role_loop(
    *,
    profile: dict[str, Any],
    role: str,
    device: str | None,
    group: dict[str, Any] | None,
    baud: int,
    log_path: str | None,
    timeout: float,
    read_timeout: float,
    chunk_size: int,
    reconnect: bool,
    reconnect_interval: float,
    tee: bool,
    expect_data: bool,
    initial_serial: serial.Serial | None = None,
    start_event: threading.Event | None = None,
    reader_ready_event: threading.Event | None = None,
    stop_event: threading.Event | None = None,
) -> dict[str, Any]:
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    result: dict[str, Any] = {
        "role": role,
        "log": log_path,
        "started": started,
        "ended": "",
        "opened_at": "",
        "first_byte_at": "",
        "bytes": 0,
        "opens": 0,
        "disconnects": 0,
        "reconnects": 0,
        "status": 0,
        "state": "starting",
        "expect_data": expect_data,
        "connected_at_end": False,
        "last_device": "",
        "last_error": "",
    }
    touch_log(log_path)
    ser = initial_serial
    if ser is not None:
        result["opens"] = 1
        result["opened_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        result["last_device"] = str(getattr(ser, "port", device) or device or "")

    if start_event is not None:
        start_event.wait()
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline and not (
        stop_event is not None and stop_event.is_set()
    ):
        if ser is None:
            selected = resolve_device(profile, role, device, group=group)
            result["last_device"] = selected
            is_reconnect = bool(result["opens"] or result["last_error"])
            if is_reconnect:
                result["reconnects"] += 1
            try:
                ser = open_serial(selected, baud, read_timeout)
                result["opens"] += 1
                if not result["opened_at"]:
                    result["opened_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                if is_reconnect:
                    append_log(
                        log_path,
                        f"[serial-console reconnected: {selected}]\n".encode(),
                    )
            except (serial.SerialException, OSError) as exc:
                result["last_error"] = str(exc)
                if not reconnect:
                    result["status"] = 1
                    break
                time.sleep(reconnect_interval)
                continue

        try:
            data = ser.read(chunk_size)
            # A port being open is weaker than a reader having entered and
            # completed its first timed read. Reset may start only after this.
            if reader_ready_event is not None:
                reader_ready_event.set()
            if data:
                if not result["first_byte_at"]:
                    result["first_byte_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                result["bytes"] += len(data)
                append_log(log_path, data)
                if tee:
                    emit(data)
        except (serial.SerialException, OSError) as exc:
            result["last_error"] = str(exc)
            result["disconnects"] += 1
            append_log(log_path, f"\n[serial-console disconnect: {exc}]\n".encode())
            try:
                ser.close()
            except (serial.SerialException, OSError):
                pass
            ser = None
            if not reconnect:
                result["status"] = 1
                break

    if ser is not None:
        result["connected_at_end"] = True
        try:
            ser.close()
        except (serial.SerialException, OSError) as exc:
            result["last_error"] = str(exc)
            result["connected_at_end"] = False

    if result["opens"] == 0:
        result["state"] = "not-opened"
        result["status"] = 1
    elif not result["connected_at_end"]:
        result["state"] = "disconnected"
        result["status"] = 1
    elif result["bytes"] == 0:
        result["state"] = "empty"
        result["status"] = 2 if expect_data else 0
    else:
        result["state"] = "data"
    result["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    return result


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------
def print_adapter_groups(groups: list[dict[str, Any]]) -> None:
    print(f"detected adapters: {len(groups)}")
    for index, group in enumerate(groups, 1):
        identity = group.get("serial") or group.get("key")
        print(
            f"  [{index}] {group.get('usb_id') or 'usb-id-unknown'} "
            f"{group.get('product') or 'USB serial adapter'} "
            f"interfaces={len(group['interfaces'])} id={identity}"
        )
        for interface in group["interfaces"]:
            print(
                f"      order={interface['order']} {interface['interface']} "
                f"{interface['device']} serial={interface['serial_number']}"
            )


def cmd_list(args: argparse.Namespace) -> int:
    profile = load_profile(args.board) if args.board else {}
    groups = discover_adapter_groups()

    print("serial adapters:")
    print_adapter_groups(groups)
    report_adapter_health(groups)

    if profile:
        print(f"board: {args.board}")
        print(f"profile_status: {profile.get('profile_status', 'unknown')}")
        print(f"baudrate: {profile_baud(profile, args.baud)}")

        group, error = select_adapter_group(groups, profile, None)
        detected = interface_map(group)
        for role, entry in get_ports(profile).items():
            interface = port_interface(entry)
            actual = detected.get(interface)
            device = actual["device"] if actual else "<missing>"
            desc = entry.get("description", "")
            present = "present" if actual else "missing"
            print(
                f"  {role}: {interface or '?'} {device} [{present}]"
                + (f" ({desc})" if desc else "")
            )
        if error:
            print(f"profile match: {error}")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    groups = discover_adapter_groups()
    print_adapter_groups(groups)
    report_adapter_health(groups)
    profile = load_profile(args.board) if args.board else None

    if not profile:
        if args.adapter:
            group, error = select_adapter_group(groups, None, args.adapter)

            if error:
                print(f"probe error: {error}", file=sys.stderr)
                return 1
            print(f"selected adapter: {group['key']}")
        return 0 if groups else 1

    group, selection_error = select_adapter_group(groups, profile, args.adapter)
    result = probe_profile(profile, group)
    if selection_error:
        result["errors"] = [selection_error]

    print(f"board: {args.board}")
    print(f"profile_status: {result['profile_status']}")
    if group:
        print(f"selected adapter: {group['key']}")
    for port in result["ports"]:
        flags = []
        if port.get("required"):
            flags.append("required")
        if port.get("default_capture"):
            flags.append("default-capture")
        flags.append(str(port.get("status") or "unknown"))
        sources = ",".join(str(item) for item in port.get("log_sources") or [])
        print(
            f"  {port['role']}: order={port.get('order') or '?'} "
            f"{port.get('interface') or '?'} "
            f"{port.get('device') or '<missing>'} "
            f"[{','.join(flags)}]"
            + (f" logs={sources}" if sources else "")
        )
    for warning in result["warnings"]:
        print(f"warning: {warning}")
    for error in result["errors"]:
        print(f"error: {error}", file=sys.stderr)
    return 1 if result["errors"] else 0


def cmd_prepare(args: argparse.Namespace) -> int:
    # Windows has no stty; pyserial applies 8N1 framing on open. This command
    # verifies that every selected role can be opened with the target baud.
    profile = load_profile(args.board)
    baud = profile_baud(profile, args.baud)
    if args.stop_modemmanager:
        print("prepare: --stop-modemmanager is a no-op on Windows")

    ports = get_ports(profile)
    roles = args.role or [
        role
        for role, _ in sorted(
            ports.items(),
            key=lambda item: int(item[1].get("order") or 999),
        )
    ]
    groups = discover_adapter_groups()
    group, error = select_adapter_group(groups, profile, args.adapter)
    if error:
        print(f"prepare error: {error}", file=sys.stderr)
        return 1
    status = 0
    for role in roles:
        device = resolve_device(profile, role, None, group=group, require_present=True)
        try:
            with open_serial(device, baud, 0.1):
                pass
            print(f"{role}: {device}: open ok @ {baud} 8N1")
        except (serial.SerialException, OSError) as exc:
            print(f"{role}: {device}: open failed: {exc}", file=sys.stderr)
            status = 1
    return status


def cmd_capture(args: argparse.Namespace) -> int:
    profile = load_profile(args.board) if args.board else {}
    baud = profile_baud(profile, args.baud)
    if not args.device and not args.role:
        print("capture error: pass --role or --device", file=sys.stderr)
        return 1
    if not args.device and not args.board:
        print("capture error: --role requires --board; otherwise pass --device", file=sys.stderr)
        return 1
    group = None
    if not args.device:
        groups = discover_adapter_groups()
        group, error = select_adapter_group(groups, profile, args.adapter)
        if error:
            print(f"capture error: {error}", file=sys.stderr)
            return 1
    result = capture_role_loop(
        profile=profile,
        role=args.role or "explicit-device",
        device=args.device,
        group=group,
        baud=baud,
        log_path=args.log,
        timeout=args.timeout,
        read_timeout=args.read_timeout,
        chunk_size=args.chunk_size,
        reconnect=args.reconnect,
        reconnect_interval=args.reconnect_interval,
        tee=True,
        expect_data=args.expect_data,
    )
    print(
        f"\nserial-console: role={result['role']} state={result['state']} "
        f"bytes={result['bytes']} reconnects={result['reconnects']}",
        file=sys.stderr,
    )
    return int(result["status"])


def cmd_capture_set(args: argparse.Namespace) -> int:
    ready_path = Path(args.ready_file) if args.ready_file else None
    if ready_path:
        try:
            ready_path.unlink(missing_ok=True)
        except OSError as exc:
            print(
                f"capture-set error: cannot clear stale ready file {ready_path}: {exc}",
                file=sys.stderr,
            )
            return 1

    groups = discover_adapter_groups()
    profile = load_profile(args.board) if args.board else None
    group, selection_error = select_adapter_group(groups, profile, args.adapter)
    if selection_error:
        print(f"capture-set error: {selection_error}", file=sys.stderr)
        print_adapter_groups(groups)
        return 1
    if profile is None:
        profile = build_discovery_profile(group)

    baud = profile_baud(profile, args.baud)
    roles = args.role or default_capture_roles(profile)
    log_dir = Path(args.log_dir)
    name = args.name or time.strftime("%Y%m%d-%H%M%S")
    log_dir.mkdir(parents=True, exist_ok=True)
    expect_data = set(args.expect_data or [])
    if args.require_data:
        expect_data.update(roles)

    unknown_roles = [role for role in roles if role not in get_ports(profile)]
    if unknown_roles:
        print(
            f"capture-set error: unknown roles: {', '.join(unknown_roles)}",
            file=sys.stderr,
        )
        return 1
    invalid_expectations = sorted(expect_data - set(roles))
    if invalid_expectations:
        print(
            "capture-set error: --expect-data roles not in capture set: "
            + ", ".join(invalid_expectations),
            file=sys.stderr,
        )
        return 1

    probe = probe_profile(profile, group)
    if probe["errors"]:
        for error in probe["errors"]:
            print(f"capture-set error: {error}", file=sys.stderr)
        return 1

    if args.stop_modemmanager:
        print("capture-set: --stop-modemmanager is a no-op on Windows")

    if args.prepare:
        for role in roles:
            device = resolve_device(
                profile, role, None, group=group, require_present=True
            )
            try:
                with open_serial(device, baud, 0.1):
                    pass
                print(f"prepare {role}: {device}: open ok")
            except (serial.SerialException, OSError) as exc:
                print(f"capture-set error: prepare failed for {role}: {exc}", file=sys.stderr)
                return 1

    results: dict[str, dict[str, Any]] = {}
    threads: list[threading.Thread] = []
    opened: dict[str, serial.Serial] = {}
    devices: dict[str, str] = {}
    session_started = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    try:
        for role in roles:
            device = resolve_device(
                profile, role, None, group=group, require_present=True
            )
            devices[role] = device
            opened[role] = open_serial(device, baud, args.read_timeout)
            print(f"opened {role}: {device}")
    except (serial.SerialException, OSError, SystemExit) as exc:
        for ser in opened.values():
            try:
                ser.close()
            except (serial.SerialException, OSError):
                pass
        print(f"capture-set error: failed to open all roles: {exc}", file=sys.stderr)
        return 1

    start_event = threading.Event()
    stop_event = threading.Event()
    reader_ready_events = {role: threading.Event() for role in roles}
    stop_reason = {"value": ""}

    def request_stop(signum: int, _frame: Any) -> None:
        stop_reason["value"] = signal.Signals(signum).name
        stop_event.set()

    previous_sigterm_handler = None
    try:
        previous_sigterm_handler = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, request_stop)
    except (ValueError, OSError, AttributeError):
        previous_sigterm_handler = None

    def run_role(role: str) -> None:
        log_path = str(log_dir / f"{name}-{role}.log")
        results[role] = capture_role_loop(
            profile=profile,
            role=role,
            device=devices[role],
            group=group,
            baud=baud,
            log_path=log_path,
            timeout=args.timeout,
            read_timeout=args.read_timeout,
            chunk_size=args.chunk_size,
            reconnect=not args.no_reconnect,
            reconnect_interval=args.reconnect_interval,
            tee=False,
            expect_data=role in expect_data,
            initial_serial=opened[role],
            start_event=start_event,
            reader_ready_event=reader_ready_events[role],
            stop_event=stop_event,
        )

    for role in roles:
        thread = threading.Thread(target=run_role, args=(role,), daemon=False)
        thread.start()
        threads.append(thread)

    try:
        start_event.set()
        ready_deadline = time.monotonic() + 5.0
        not_ready = []
        for role in roles:
            remaining = max(0.0, ready_deadline - time.monotonic())
            if not reader_ready_events[role].wait(remaining):
                not_ready.append(role)
        if not_ready:
            stop_reason["value"] = "reader-start-timeout"
            stop_event.set()
            for thread in threads:
                thread.join()
            print(
                "capture-set error: readers did not enter the read loop: "
                + ", ".join(not_ready),
                file=sys.stderr,
            )
            return 1
        if ready_path:
            ready_path.parent.mkdir(parents=True, exist_ok=True)
            ready_path.write_text(
                "schema_version: 1\n"
                "state: active\n"
                f"pid: {os.getpid()}\n"
                f"board: {args.board or 'unclassified'}\n"
                f"name: {name}\n"
                f"started: {session_started}\n"
                f"roles: {','.join(roles)}\n",
                encoding="utf-8",
            )
        print(f"ALL PORTS READY: {', '.join(roles)}; capture is active", flush=True)

        try:
            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            stop_reason["value"] = "KeyboardInterrupt"
            stop_event.set()
            print("\ncapture-set: stop requested; finalizing session", flush=True)
            for thread in threads:
                thread.join()
    finally:
        if previous_sigterm_handler is not None:
            try:
                signal.signal(signal.SIGTERM, previous_sigterm_handler)
            except (ValueError, OSError, AttributeError):
                pass
        if ready_path:
            try:
                ready_path.unlink(missing_ok=True)
            except OSError as exc:
                print(
                    f"capture-set warning: cannot remove ready file {ready_path}: {exc}",
                    file=sys.stderr,
                )

    summary_path = log_dir / f"{name}-serial-session.txt"
    yaml_summary_path = log_dir / f"{name}-serial-session.yaml"
    session_ended = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    session_data = {
        "schema_version": 1,
        "board": args.board or "unclassified",
        "profile_status": profile.get("profile_status", "unknown"),
        "adapter": {
            "key": group.get("key", ""),
            "serial": group.get("serial", ""),
            "usb_id": group.get("usb_id", ""),
            "interfaces": len(group.get("interfaces", [])),
        },
        "name": name,
        "started": session_started,
        "ended": session_ended,
        "timeout": args.timeout,
        "baud": baud,
        "reconnect": not args.no_reconnect,
        "stop_reason": stop_reason["value"],
        "roles": {role: results.get(role, {}) for role in roles},
    }
    with yaml_summary_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(session_data, handle, sort_keys=False, allow_unicode=False)

    with summary_path.open("w", encoding="utf-8") as handle:
        handle.write(f"board: {args.board or 'unclassified'}\n")
        handle.write(f"profile_status: {profile.get('profile_status', 'unknown')}\n")
        handle.write(f"name: {name}\n")
        handle.write(f"started: {session_started}\n")
        handle.write(f"ended: {session_ended}\n")
        handle.write(f"timeout: {args.timeout}\n")
        handle.write(f"baud: {baud}\n")
        handle.write(f"reconnect: {not args.no_reconnect}\n")
        handle.write(f"stop_reason: {stop_reason['value']}\n")
        for role in roles:
            result = results.get(role, {})
            handle.write("\n")
            handle.write(f"[{role}]\n")
            for key in (
                "log",
                "started",
                "ended",
                "opened_at",
                "first_byte_at",
                "last_device",
                "bytes",
                "opens",
                "disconnects",
                "reconnects",
                "connected_at_end",
                "expect_data",
                "state",
                "status",
                "last_error",
            ):
                handle.write(f"{key}: {result.get(key, '')}\n")

    print(f"summary: {summary_path}")
    print(f"summary-yaml: {yaml_summary_path}")
    for role in roles:
        result = results.get(role, {})
        print(
            f"{role}: state={result.get('state')} status={result.get('status')} "
            f"bytes={result.get('bytes')} "
            f"reconnects={result.get('reconnects')} log={result.get('log')}"
        )
    statuses = [int(results.get(role, {}).get("status", 1)) for role in roles]
    if any(status == 1 for status in statuses):
        return 1
    if any(status == 2 for status in statuses):
        return 2
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    profile = load_profile(args.board)
    group = None
    if not args.device:
        group, error = select_adapter_group(discover_adapter_groups(), profile, args.adapter)
        if error:
            raise SystemExit(error)
    device = resolve_device(
        profile, args.role, args.device, group=group, require_present=True
    )
    baud = profile_baud(profile, args.baud)
    line_ending = decode_escapes(args.line_ending)
    with open_serial(device, baud, args.read_timeout) as ser:
        for command in args.cmd:
            payload = command.encode() + line_ending
            ser.write(payload)
            append_log(args.log, payload)
        if args.capture_after > 0:
            deadline = time.monotonic() + args.capture_after
            while time.monotonic() < deadline:
                data = ser.read(args.chunk_size)
                if data:
                    append_log(args.log, data)
                    emit(data)
    return 0


def cmd_uboot_stop(args: argparse.Namespace) -> int:
    profile = load_profile(args.board)
    group = None
    if not args.device:
        group, error = select_adapter_group(discover_adapter_groups(), profile, args.adapter)
        if error:
            raise SystemExit(error)
    device = resolve_device(
        profile, args.role, args.device, group=group, require_present=True
    )
    baud = profile_baud(profile, args.baud)
    trigger = args.trigger.encode()
    prompt_re = re.compile(args.prompt.encode())
    deadline = time.monotonic() + args.timeout
    seen = bytearray()
    sent = False

    with open_serial(device, baud, args.read_timeout) as ser:
        while time.monotonic() < deadline:
            data = ser.read(args.chunk_size)
            if data:
                seen.extend(data)
                append_log(args.log, data)
                emit(data)
                if not sent and trigger in seen:
                    payload = decode_escapes(args.interrupt)
                    ser.write(payload)
                    append_log(args.log, payload)
                    sent = True
                if sent and prompt_re.search(bytes(seen)):
                    return 0

    if not sent:
        print("\ntrigger not seen before timeout", file=sys.stderr)
        return 2
    print("\nprompt not seen after interrupt", file=sys.stderr)
    return 3


def _shell_windows(ser: serial.Serial, log_path: str | None) -> None:
    stop = threading.Event()

    def reader() -> None:
        while not stop.is_set():
            try:
                data = ser.read(4096)
            except (serial.SerialException, OSError):
                break
            if data:
                append_log(log_path, data)
                emit(data)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    try:
        while True:
            ch = msvcrt.getwch()  # type: ignore[union-attr]
            if ch in ("\x00", "\xe0"):
                # Function/arrow keys: swallow the following scan code.
                msvcrt.getwch()  # type: ignore[union-attr]
                continue
            if ch == "\x1d":  # Ctrl-]
                break
            payload = ch.encode("utf-8", errors="replace")
            ser.write(payload)
            append_log(log_path, payload)
    finally:
        stop.set()
        thread.join(timeout=1.0)


def _shell_posix(ser: serial.Serial, log_path: str | None) -> None:
    old_attrs = termios.tcgetattr(sys.stdin)  # type: ignore[union-attr]
    try:
        tty.setraw(sys.stdin.fileno())  # type: ignore[union-attr]
        while True:
            readable, _, _ = select.select([sys.stdin, ser], [], [])  # type: ignore[union-attr]
            if ser in readable:
                data = ser.read(4096)
                append_log(log_path, data)
                emit(data)
            if sys.stdin in readable:
                data = os.read(sys.stdin.fileno(), 1024)
                if data in {b"\x1d", b"\x1d\r", b"\x1d\n"}:
                    break
                ser.write(data)
                append_log(log_path, data)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_attrs)  # type: ignore[union-attr]


def cmd_shell(args: argparse.Namespace) -> int:
    profile = load_profile(args.board)
    group = None
    if not args.device:
        group, error = select_adapter_group(discover_adapter_groups(), profile, args.adapter)
        if error:
            raise SystemExit(error)
    device = resolve_device(
        profile, args.role, args.device, group=group, require_present=True
    )
    baud = profile_baud(profile, args.baud)
    print(f"serial-console: interactive shell on {device} @ {baud}; exit with Ctrl-]",
          file=sys.stderr)
    with open_serial(device, baud, 0.05 if IS_WINDOWS else 0) as ser:
        if IS_WINDOWS and msvcrt is not None:
            _shell_windows(ser, args.log)
        elif termios is not None:
            _shell_posix(ser, args.log)
        else:
            raise SystemExit("no interactive backend available on this platform")
    return 0


def cmd_recover(args: argparse.Namespace) -> int:
    # Windows has no sysfs driver rebind. A missing interface after BCU takes
    # over an FTDI channel usually means the COM port disappeared. Report the
    # missing interfaces and ask the operator to replug or wait for
    # re-enumeration.
    profile = load_profile(args.board)
    groups = discover_adapter_groups()
    group, error = select_adapter_group(groups, profile, args.adapter)
    if error:
        print(f"recover error: {error}", file=sys.stderr)
        return 1

    detected = interface_map(group)
    missing = []
    for role, entry in get_ports(profile).items():
        interface = port_interface(entry)
        if interface and interface not in detected:
            missing.append((role, interface))

    if not missing:
        print("recover: all profile interfaces are present; nothing to do")
        return 0

    print("recover: the following profile interfaces are not enumerated:")
    for role, interface in missing:
        print(f"  {role}: {interface}")
    print(
        "recover: Windows cannot rebind a USB serial driver from the command "
        "line. If a board control tool (BCU) took the channel, close it, then "
        "replug the adapter or toggle it in Device Manager and re-probe."
    )
    return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    groups = discover_adapter_groups()
    print_adapter_groups(groups)
    if not groups:
        print("doctor: no USB serial adapter detected", file=sys.stderr)
        return 1
    worst = report_adapter_health(groups)
    if getattr(args, "verify_eeprom", None) and worst != "ok":
        if not args.board:
            print(
                "doctor: --verify-eeprom needs --board=<model> to pass to bcu",
                file=sys.stderr,
            )
            return 1
        if len(groups) != 1 or groups[0].get("usb_id") != "0403:6011":
            print(
                "doctor: --verify-eeprom requires exactly one FTDI FT4232H "
                "adapter; BCU read not attempted",
                file=sys.stderr,
            )
            return 1
        verdict = verify_eeprom_with_bcu(args.verify_eeprom, args.board)
        if not verdict["ran"] or verdict["error"]:
            print(
                f"doctor: EEPROM verification failed ({verdict['error']}); "
                "EEPROM state is unknown",
                file=sys.stderr,
            )
            return 1
        echoed = verdict.get("echoed_board")
        if echoed:
            print(
                f"doctor: note 'board model is {echoed}' is only an echo "
                f"of -board={args.board}, not a confirmed identity"
            )
        print(f"doctor: bcu eeprom state = {verdict['state']} ({verdict['detail']})")
        if verdict["state"] == "unknown":
            print(
                "doctor: BCU did not establish the EEPROM state; "
                "interface identity cannot resolve that uncertainty"
            )
    if worst == "ok":
        print("doctor: all adapters expose a stable per-interface identity")
        return 0
    if worst == "blank":
        print(
            "doctor: at least one adapter has unresolved interface identities; "
            "do not guess roles. Capture only an independently identified "
            "--device COMn or resolve USB/driver enumeration first",
            file=sys.stderr,
        )
        return 1
    print(
        "doctor: adapter identity recovered from the Windows registry fallback; "
        "the interface mapping is usable on this host. This result alone does "
        "not justify an EEPROM write",
        file=sys.stderr,
    )
    return 2


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------
def add_common(parser: argparse.ArgumentParser, *, require_board: bool = True) -> None:
    parser.add_argument("--board", required=require_board, help="packaged board profile id")

    parser.add_argument("--role", help="serial role from the packaged board profile")
    parser.add_argument("--device", help="explicit serial device, e.g. COM155")
    parser.add_argument("--adapter", help="adapter base serial or VID:PID")
    parser.add_argument("--baud", type=int, help="override baudrate")
    parser.add_argument("--log", help="append raw serial data to this log file")
    parser.add_argument("--read-timeout", type=float, default=0.1)
    parser.add_argument("--chunk-size", type=int, default=512)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NXP lab serial console wrapper (Windows)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list serial devices and board role mappings")
    p_list.add_argument("--board", help="optional packaged board profile id")
    p_list.add_argument("--baud", type=int, help="override baudrate")
    p_list.set_defaults(func=cmd_list)

    p_probe = sub.add_parser("probe", help="detect adapters and validate a board serial profile")
    p_probe.add_argument("--board", help="optional packaged board profile id")
    p_probe.add_argument("--adapter", help="adapter base serial or VID:PID")
    p_probe.set_defaults(func=cmd_probe)

    p_doctor = sub.add_parser(
        "doctor",
        help="check interface identity without inferring EEPROM contents",
    )
    p_doctor.add_argument("--board", help="board model for an optional BCU EEPROM read")
    p_doctor.add_argument(
        "--verify-eeprom",
        metavar="BCU",
        help=(
            "path to bcu(.exe); when an adapter looks blank/degraded, run "
            "'bcu eeprom -r -board=<board>' on a single FT4232H adapter; "
            "report readback evidence without authorizing writes (needs --board)"
        ),
    )
    p_doctor.set_defaults(func=cmd_doctor)


    p_recover = sub.add_parser(
        "recover",
        help="report profile interfaces that are not currently enumerated",
    )
    p_recover.add_argument("--board", required=True)
    p_recover.add_argument("--adapter", help="adapter base serial or VID:PID")
    p_recover.set_defaults(func=cmd_recover)

    p_prepare = sub.add_parser("prepare", help="verify board serial roles can be opened")
    p_prepare.add_argument("--board", required=True)
    p_prepare.add_argument("--role", action="append", help="role to prepare; default: all roles")
    p_prepare.add_argument("--adapter", help="adapter base serial or VID:PID")
    p_prepare.add_argument("--baud", type=int, help="override baudrate")
    p_prepare.add_argument("--stop-modemmanager", action="store_true")
    p_prepare.set_defaults(func=cmd_prepare)

    p_capture = sub.add_parser("capture", help="capture serial output")
    add_common(p_capture, require_board=False)
    p_capture.add_argument("--timeout", type=float, default=30.0)
    p_capture.add_argument("--reconnect", action="store_true", help="reopen the serial port after disconnect")
    p_capture.add_argument("--reconnect-interval", type=float, default=0.2)
    p_capture.add_argument("--expect-data", action="store_true", help="return 2 if the capture is empty")
    p_capture.set_defaults(func=cmd_capture)

    p_capture_set = sub.add_parser("capture-set", help="capture multiple board roles into separate logs")
    p_capture_set.add_argument("--board", help="board profile; omit to capture one unclassified adapter")
    p_capture_set.add_argument("--adapter", help="adapter base serial or VID:PID")
    p_capture_set.add_argument("--role", action="append", help="role to capture; default comes from board profile")
    p_capture_set.add_argument("--baud", type=int, help="override baudrate")
    p_capture_set.add_argument("--log-dir", required=True)
    p_capture_set.add_argument("--name", help="log filename prefix; default is a timestamp")
    p_capture_set.add_argument("--timeout", type=float, default=90.0)
    p_capture_set.add_argument("--read-timeout", type=float, default=0.1)
    p_capture_set.add_argument("--chunk-size", type=int, default=512)
    p_capture_set.add_argument("--reconnect-interval", type=float, default=0.2)
    p_capture_set.add_argument("--no-reconnect", action="store_true")
    p_capture_set.add_argument("--prepare", action="store_true")
    p_capture_set.add_argument("--stop-modemmanager", action="store_true")
    p_capture_set.add_argument("--expect-data", action="append", help="role that must receive at least one byte")
    p_capture_set.add_argument("--require-data", action="store_true", help="require data on every selected role")
    p_capture_set.add_argument(
        "--ready-file",
        help="active marker: create after every selected port is open and remove when capture ends",
    )
    p_capture_set.set_defaults(func=cmd_capture_set)

    p_send = sub.add_parser("send", help="send commands to a serial port")
    add_common(p_send)
    p_send.add_argument("--cmd", action="append", required=True)
    p_send.add_argument("--line-ending", default="\r")
    p_send.add_argument("--capture-after", type=float, default=2.0)
    p_send.set_defaults(func=cmd_send)

    p_stop = sub.add_parser("uboot-stop", help="wait for autoboot prompt and interrupt")
    add_common(p_stop)
    p_stop.add_argument("--timeout", type=float, default=10.0)
    p_stop.add_argument("--trigger", default="Hit any key to stop autoboot")
    p_stop.add_argument("--interrupt", default="\r")
    p_stop.add_argument("--prompt", default=rb"(=>|U-Boot[#>])".decode())
    p_stop.set_defaults(func=cmd_uboot_stop)

    p_shell = sub.add_parser("shell", help="interactive serial shell; exit with Ctrl-]")
    add_common(p_shell)
    p_shell.set_defaults(func=cmd_shell)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (serial.SerialException, OSError) as exc:
        print(f"serial-console: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
