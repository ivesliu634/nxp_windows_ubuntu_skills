#!/usr/bin/env python3
"""No-board self-check for the Windows serial-console tool.

Validates that serial_console.py imports cleanly and that every board profile
under profiles/ parses as YAML and carries the schema-3 fields that the tool
reads at runtime. This runs without a board attached; it does not open COM
ports. Exit code 0 means all checks passed, 1 means at least one failed.
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REQUIRED_TOP = ("schema_version", "board", "adapter", "ports")
REQUIRED_PORT = ("order", "interface")


def check_yaml():
    try:
        import yaml
    except ImportError:
        print("FAIL: PyYAML not installed")
        return False
    files = sorted(glob.glob(os.path.join(HERE, "profiles", "*", "serial.yaml")))
    print("found %d profile(s)" % len(files))
    if not files:
        print("FAIL: no profiles found")
        return False
    ok = True
    for f in files:
        name = os.path.basename(os.path.dirname(f))
        try:
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except Exception as exc:  # noqa: BLE001
            print("FAIL parse %s: %s" % (name, exc))
            ok = False
            continue
        if not isinstance(data, dict):
            print("FAIL schema %s: profile root is not a mapping" % name)
            ok = False
            continue
        missing = [k for k in REQUIRED_TOP if k not in data]
        ports = data.get("ports", {}) or {}
        bad_ports = []
        for role, cfg in ports.items():
            if not isinstance(cfg, dict):
                bad_ports.append(role + "(not-a-map)")
                continue
            for k in REQUIRED_PORT:
                if k not in cfg:
                    bad_ports.append("%s(no-%s)" % (role, k))
        if missing or bad_ports:
            print("SCHEMA_WARN %s missing=%s bad_ports=%s"
                  % (name, missing, bad_ports))
            ok = False
        else:
            print("PARSE_OK %s board=%s roles=%s"
                  % (name, data.get("board"), list(ports.keys())))
    return ok


def check_import():
    # Import the tool module to catch any load-time errors beyond py_compile
    # (bad default args, top-level exceptions, etc.).
    import importlib.util
    path = os.path.join(HERE, "serial_console.py")
    spec = importlib.util.spec_from_file_location("serial_console", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        print("FAIL: importing serial_console triggered SystemExit")
        return False
    except Exception as exc:  # noqa: BLE001
        print("FAIL import serial_console: %s" % exc)
        return False
    print("IMPORT_OK serial_console")
    return True


def main():
    print("== serial-console no-board self-check ==")
    imp = check_import()
    yml = check_yaml()
    good = imp and yml
    print("RESULT", "ALL_GOOD" if good else "HAS_FAILURES")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
