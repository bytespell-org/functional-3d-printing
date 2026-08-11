#!/usr/bin/env python3
"""Append one functional-print iteration record to a JSONL log."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--part", required=True)
    parser.add_argument("--revision", default="unknown")
    parser.add_argument("--stage", required=True, choices=("small-test", "prototype", "full-print"))
    parser.add_argument("--printer", default="unknown")
    parser.add_argument("--nozzle", default="unknown")
    parser.add_argument("--material", default="unknown")
    parser.add_argument("--profile", default="unknown")
    parser.add_argument("--defect", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--cause", required=True)
    parser.add_argument("--change", required=True)
    parser.add_argument("--result", required=True, choices=("pending", "failed", "improved", "passed"))
    parser.add_argument(
        "--promotion", default="no", choices=("no", "candidate", "validated", "promoted")
    )
    args = parser.parse_args()

    record = {
        "schema_version": 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "part": args.part,
        "revision": args.revision,
        "stage": args.stage,
        "printer": args.printer,
        "nozzle": args.nozzle,
        "material": args.material,
        "profile": args.profile,
        "defect": args.defect,
        "evidence": args.evidence,
        "cause": args.cause,
        "change": args.change,
        "result": args.result,
        "promotion": args.promotion,
    }
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, "log": str(args.log), "record": record}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
