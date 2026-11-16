#!/usr/bin/env python3
"""Check a board schematic PDF for whether the on-board FTDI bridge serial
EEPROM is actually populated or marked DNP (Do Not Populate).

Scope / portability
-------------------
This is an OPTIONAL, offline corroboration step and needs a schematic PDF, which
a customer may not provide. It is NOT the primary check. The primary, board-
agnostic way to tell whether a board-level FTDI bridge identity is written (and
whether writing can ever work) is the behavioural check in serial_console.py
(doctor): a bare serial with no A/B/C/D interface letter means the identity is
not written, and if repeated "bcu eeprom -w" + USB replug never changes the
serial (and bcu never prints "Registered FTDI EEPROM on board") the EEPROM is
almost certainly not populated (DNP). That behavioural path works on any board,
including customer boards, with no schematic. Use this PDF checker only when a
schematic is available and you want to confirm DNP before touching hardware.

Why this exists
---------------
When "bcu eeprom -w -board=<model>" reports success but nothing changes (the
serial console stays a bare "5", doctor stays degraded, -auto keeps failing),
there are two very different root causes:

  1. the FTDI EEPROM chip IS on the board but blank  -> writing WILL work.
  2. the FTDI EEPROM chip is DNP / not populated      -> writing can NEVER
     persist an identity, no matter how many times you replug.

Case 2 was hit on the i.MX8MP EVK base board: the FT4232H serial-EEPROM pins
(EECS/EECLK/EEDATA) have no EEPROM part number and only DNP placeholders on the
schematic, so there is no chip to write. This tool turns that manual PDF hunt
into one repeatable command so the same confusion does not come back.

Discriminator (validated on two real boards)
--------------------------------------------
The deciding signal is whether the EEPROM circuit page carries an actual EEPROM
PART NUMBER (93LC56, 93C46, ...):
  - i.MX93 EVK: the EEPROM page prints "93LC56BT" and the chip IS fitted (bcu
    wrote SN E10092). The DNP marks on that page are neighbouring no-fit jumper
    resistors, NOT the EEPROM -> verdict populated.
  - i.MX8MP EVK base board: the EEPROM page has NO part number, only DNP marks
    around EECS/EECLK/EEDATA -> verdict dnp (no chip to write).

What it does
------------
- resolves a schematic PDF either from --pdf, or from --board/--soc by looking
  under a support-level SoC_material tree (support_level/SoC_material/<soc>/hardware/*.pdf).
- extracts text page by page (pypdf), finds the page(s) that carry the FTDI
  USB-UART bridge serial-EEPROM interface pins (EECS/EECLK/EEDATA, FT_EE*).
- decides populated vs dnp using the part-number rule above, and always prints
  the evidence lines so a human can re-check.

This is a heuristic over extracted text (layout is lost), so the evidence lines
are always printed. Exit codes:
  0 = populated (EEPROM present; bcu eeprom -w can work once written)
  3 = dnp (EEPROM not populated; bcu eeprom -w can never persist identity)
  2 = unknown (bridge EEPROM pins not found in this PDF; inspect manually)
  1 = error (no PDF found, cannot read, etc.)

ASCII-only source per repo convention.
"""
import argparse
import logging
import os
import re
import sys

# pypdf is noisy about missing fontTools; that warning is irrelevant here.
logging.getLogger("pypdf").setLevel(logging.ERROR)

# FTDI USB-UART bridge parts whose external serial config EEPROM is optional.
BRIDGE_PARTS = ("FT4232H", "FT2232H", "FT232H", "FT232R", "FT231X", "FT230X")

# Signal names of the FTDI external serial EEPROM (93C46/93C56 style) interface.
EEPROM_PIN_PATTERNS = [
    re.compile(r"\bEECS\b", re.I),
    re.compile(r"\bEECLK\b", re.I),
    re.compile(r"\bEEDATA\b", re.I),
    re.compile(r"\bFT_EE", re.I),
    re.compile(r"\bEE_?CS\b", re.I),
]

DNP_PATTERN = re.compile(r"\bDNP\b", re.I)
# Populated EEPROM part markings sometimes appear near the pins.
EEPROM_PART_PATTERN = re.compile(r"93C\d{2}|93LC\d{2}|AT93|M95\d", re.I)


def eprint(*a):
    print(*a, file=sys.stderr)


def find_soc_dir(material_root, board):
    """Longest-prefix match of the board id against SoC_material subdirs.

    imx8mpevk -> imx8mp, imx93evk14 -> imx93, imx943evk19b1 -> imx943.
    """
    if not os.path.isdir(material_root):
        return None
    board = board.lower()
    best = None
    for name in os.listdir(material_root):
        full = os.path.join(material_root, name)
        if not os.path.isdir(full):
            continue
        if board.startswith(name.lower()):
            if best is None or len(name) > len(best):
                best = name
    return best


def list_hardware_pdfs(material_root, soc):
    hw = os.path.join(material_root, soc, "hardware")
    out = []
    for root, _dirs, files in os.walk(hw):
        for f in files:
            if f.lower().endswith(".pdf"):
                out.append(os.path.join(root, f))
    return sorted(out)


def scan_pdf(path):
    """Return list of hits: dicts with page, bridge, has_eeprom_pins,
    dnp_count, part_marking, evidence lines. Only pages that mention an EEPROM
    pin OR a bridge part are returned."""
    import pypdf

    reader = pypdf.PdfReader(path)
    hits = []
    for idx, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            continue
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        joined = "\n".join(lines)
        has_pins = any(p.search(joined) for p in EEPROM_PIN_PATTERNS)
        bridge = next((b for b in BRIDGE_PARTS if re.search(b, joined, re.I)), None)
        if not (has_pins or bridge):
            continue
        # collect evidence lines that matter
        ev = []
        for ln in lines:
            if (
                any(p.search(ln) for p in EEPROM_PIN_PATTERNS)
                or DNP_PATTERN.search(ln)
                or (bridge and re.search(bridge, ln, re.I))
                or EEPROM_PART_PATTERN.search(ln)
            ):
                ev.append(ln)
        hits.append({
            "page": idx + 1,
            "bridge": bridge,
            "has_pins": has_pins,
            "dnp_count": sum(1 for ln in lines if DNP_PATTERN.search(ln)),
            "part_marking": bool(EEPROM_PART_PATTERN.search(joined)),
            "evidence": ev,
        })
    return hits


def verdict_from_hits(hits):
    """Decide populated / dnp / unknown from the per-page hits.

    Key discriminator: whether the EEPROM circuit page carries an actual EEPROM
    PART NUMBER (93LC56, 93C46, ...). A part number means the chip is in the BOM
    (populated); no part number but DNP placeholders around EECS/EECLK/EEDATA
    means the footprint is a no-fit (dnp). Text extraction loses layout, so this
    is a heuristic and the evidence lines are always printed for human review."""
    pin_pages = [h for h in hits if h["has_pins"]]
    if not pin_pages:
        return "unknown", pin_pages
    part_pages = [h for h in pin_pages if h["part_marking"]]
    dnp_pages = [h for h in pin_pages if h["dnp_count"] > 0]
    # An explicit EEPROM part number on the pin page wins: the chip is in the
    # BOM. Validated on i.MX93 EVK ("93LC56BT", really fitted, bcu wrote E10092);
    # the surrounding DNP marks are neighbouring no-fit jumper resistors.
    if part_pages:
        return "populated", pin_pages
    # No part number anywhere on the EEPROM pin pages, only DNP placeholders:
    # the EEPROM footprint itself is a no-fit. Validated on i.MX8MP EVK base
    # board (no part number, all DNP around EECS/EECLK/EEDATA).
    if dnp_pages:
        return "dnp", pin_pages
    return "unknown", pin_pages


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Check if a board's FTDI bridge serial EEPROM is populated or DNP.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--pdf", help="path to a specific schematic PDF")
    src.add_argument("--board", help="board id, e.g. imx8mpevk (maps to a SoC dir)")
    ap.add_argument("--soc", help="override SoC dir name, e.g. imx8mp")
    ap.add_argument(
        "--material",
        default=os.path.join("support_level", "SoC_material"),
        help="root of the SoC_material tree (default: support_level/SoC_material)")
    ap.add_argument("--all-pages", action="store_true",
                    help="print evidence for every matched page, not just pin pages")
    args = ap.parse_args(argv)

    pdfs = []
    if args.pdf:
        if not os.path.isfile(args.pdf):
            eprint(f"error: PDF not found: {args.pdf}")
            return 1
        pdfs = [args.pdf]
    else:
        soc = args.soc or find_soc_dir(args.material, args.board)
        if not soc:
            eprint(f"error: could not map board '{args.board}' to a SoC dir under {args.material}")
            return 1
        pdfs = list_hardware_pdfs(args.material, soc)
        if not pdfs:
            eprint(f"error: no hardware PDFs under {os.path.join(args.material, soc, 'hardware')}")
            return 1
        print(f"soc dir: {soc}  ({len(pdfs)} hardware PDF(s))")

    # Rank a verdict per PDF, then report the most trustworthy finding. A PDF
    # whose EEPROM page shows a part number (populated) is more authoritative
    # than one that only has DNP placeholders, because a multi-fab schematic
    # set can contain both the real EVK page and unrelated no-fit variants.
    rank = {"unknown": 0, "dnp": 1, "populated": 2}
    overall = "unknown"
    for path in pdfs:
        print(f"\n=== {path} ===")
        try:
            hits = scan_pdf(path)
        except Exception as exc:
            eprint(f"  error reading PDF: {exc}")
            continue
        if not hits:
            print("  no FTDI bridge / EEPROM-pin pages found in this PDF")
            continue
        verdict, pin_pages = verdict_from_hits(hits)
        show = hits if args.all_pages else (pin_pages or hits)
        for h in show:
            tag = "PINS" if h["has_pins"] else "bridge-only"
            print(f"  page {h['page']}: {tag} bridge={h['bridge']} "
                  f"dnp={h['dnp_count']} part_marking={h['part_marking']}")
            for ln in h["evidence"]:
                print(f"      | {ln}")
        print(f"  --> verdict for this PDF: {verdict.upper()}")
        if rank[verdict] >= rank[overall]:
            overall = verdict

    print(f"\nRESULT: {overall.upper()}")
    if overall == "populated":
        print("The FTDI bridge serial EEPROM IS populated. "
              "If blank, bcu eeprom -w -board=<model> then replug USB will work.")
        return 0
    if overall == "dnp":
        print("The FTDI bridge serial EEPROM is NOT populated (DNP). "
              "bcu eeprom -w can never persist an identity on this board; "
              "use the registry-fallback ports to reach the console.")
        return 3
    print("Could not locate the FTDI bridge EEPROM pins in the schematic text. "
          "Inspect the PDF manually (search EECS/EECLK/EEDATA near the bridge part).")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
