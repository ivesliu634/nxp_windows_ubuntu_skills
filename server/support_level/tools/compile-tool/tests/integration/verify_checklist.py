from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from compile_tool.checklists import normalize_checklist
from compile_tool.common import ToolError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only resource contract check for the selected project checklist; not a build or board test")
    parser.add_argument("--checklist", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        normalized = normalize_checklist(args.checklist)
        recipe = normalized.get("make_recipe") or {}
        print(json.dumps({
            "check": "selected_checklist_resource_contract", "result": "passed",
            "project": normalized["project"], "parameters": normalized["parameters"],
            "m_payloads": sorted(recipe.get("required_m_payloads", {}).values()),
            "not_checked": [
                "complete native-build dependency set", "firmware release compatibility",
                "producer success-state freshness", "build execution", "board runtime",
            ],
        }, indent=2))
        return 0
    except (ToolError, OSError) as exc:
        print(f"resource contract check: FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())