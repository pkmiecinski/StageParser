"""Command-line interface for StageParser."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

import yaml

from stageparser.api import Stage


def _format_json(data: dict, indent: int = 2) -> str:
    return json.dumps(data, indent=indent, ensure_ascii=False)


def _format_yaml(data: dict) -> str:
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _format_dsv(rows: list[dict], delimiter: str) -> str:
    """Format a list of flat dicts as delimiter-separated values."""
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys(), delimiter=delimiter)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stageparser",
        description="Parse MVR stage files and extract DMX fixture data.",
    )
    parser.add_argument(
        "mvr_file",
        type=Path,
        help="Path to the .mvr file to parse.",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "yaml", "csv", "tsv"],
        default="json",
        help="Output format (default: json).",
    )
    parser.add_argument(
        "-u", "--universe",
        type=int,
        default=None,
        help="Filter output to a specific universe.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a brief summary instead of full data.",
    )
    parser.add_argument(
        "--channels",
        action="store_true",
        help="Output only channel information (flat table).",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Write output to file instead of stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    mvr_path: Path = args.mvr_file
    if not mvr_path.exists():
        print(f"Error: file not found: {mvr_path}", file=sys.stderr)
        return 1

    try:
        stage = Stage(mvr_path)
    except Exception as e:
        print(f"Error parsing MVR file: {e}", file=sys.stderr)
        return 1

    fmt: str = args.format

    if args.channels:
        rows = stage.channels_table(args.universe)
        if fmt in ("csv", "tsv"):
            delimiter = "," if fmt == "csv" else "\t"
            output = _format_dsv(rows, delimiter)
        elif fmt == "yaml":
            output = _format_yaml(rows)
        else:
            output = _format_json(rows)
    elif args.summary:
        data = stage.summary()
        if fmt in ("csv", "tsv"):
            delimiter = "," if fmt == "csv" else "\t"
            output = _format_dsv(data.get("fixtures", []), delimiter)
        elif fmt == "yaml":
            output = _format_yaml(data)
        else:
            output = _format_json(data)
    elif args.universe is not None:
        fixtures = stage.list_fixtures(args.universe)
        if fmt in ("csv", "tsv"):
            delimiter = "," if fmt == "csv" else "\t"
            output = _format_dsv([f.to_dict() for f in fixtures], delimiter)
        elif fmt == "yaml":
            output = _format_yaml({
                "universe": args.universe,
                "fixture_count": len(fixtures),
                "fixtures": [f.to_dict() for f in fixtures],
            })
        else:
            output = _format_json({
                "universe": args.universe,
                "fixture_count": len(fixtures),
                "fixtures": [f.to_dict() for f in fixtures],
            })
    else:
        if fmt in ("csv", "tsv"):
            print("Error: csv/tsv format requires --channels, --summary, or --universe.", file=sys.stderr)
            return 1
        data = stage.to_dict()
        output = _format_json(data) if fmt == "json" else _format_yaml(data)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
