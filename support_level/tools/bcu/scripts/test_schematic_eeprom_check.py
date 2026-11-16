"""Hardware-free unit check for schematic_eeprom_check.verdict_from_hits.

Feeds synthetic per-page hit dicts that mirror the REAL evidence captured from
two boards, so the populated-vs-dnp discriminator (EEPROM part number wins over
surrounding DNP jumper marks) stays covered without opening any PDF.

Run: python test_schematic_eeprom_check.py
"""
import importlib.util
from pathlib import Path

mod_path = Path(__file__).resolve().parent / "schematic_eeprom_check.py"
spec = importlib.util.spec_from_file_location("sec", mod_path)
sec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sec)


def page(has_pins, dnp, part):
    return {"page": 1, "bridge": "FT4232H", "has_pins": has_pins,
            "dnp_count": dnp, "part_marking": part, "evidence": []}


# Cases modelled on real extractor output.
cases = {
    # i.MX8MP EVK page 19: pins present, DNP marks, NO part number -> dnp.
    "imx8mp_page19": ([page(True, 6, False)], "dnp"),
    # i.MX93 EVK page 20: pins present, DNP marks AND 93LC56BT part -> populated
    # (the DNP marks are neighbouring jumper resistors, not the EEPROM).
    "imx93_page20": ([page(True, 7, True)], "populated"),
    # A block-diagram bridge mention with no EEPROM pins -> unknown.
    "bridge_only": ([page(False, 0, False)], "unknown"),
    # Pins with a part number and zero DNP -> populated.
    "clean_populated": ([page(True, 0, True)], "populated"),
    # Pins, no part, no DNP -> unknown (cannot tell either way).
    "pins_no_evidence": ([page(True, 0, False)], "unknown"),
}

failures = 0
for name, (hits, exp) in cases.items():
    got, _ = sec.verdict_from_hits(hits)
    ok = got == exp
    failures += 0 if ok else 1
    print(f"{name}: verdict={got} expected={exp} {'OK' if ok else 'FAIL'}")

# find_soc_dir longest-prefix mapping must be board-agnostic.
import tempfile
import os
with tempfile.TemporaryDirectory() as root:
    for d in ("imx8mp", "imx93", "imx943", "imx95"):
        os.makedirs(os.path.join(root, d))
    soc_cases = {"imx8mpevk": "imx8mp", "imx93evk14": "imx93",
                 "imx943evk19b1": "imx943", "imx95evk19": "imx95"}
    for board, exp in soc_cases.items():
        got = sec.find_soc_dir(root, board)
        ok = got == exp
        failures += 0 if ok else 1
        print(f"find_soc_dir[{board}]: {got} expected={exp} {'OK' if ok else 'FAIL'}")

print("RESULT:", "PASS" if failures == 0 else f"FAIL ({failures})")
raise SystemExit(1 if failures else 0)
