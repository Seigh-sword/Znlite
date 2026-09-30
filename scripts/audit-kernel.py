#!/usr/bin/env python3
"""Fail closed when Kconfig drops a requested Znlite setting.

No third-party dependencies. Can lint policy without downloading/building Linux.
A missing resolved symbol is equivalent to n (Kconfig omits invisible symbols).
With --source, policy names are also checked against upstream Kconfig definitions.
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FRAGMENTS = [ROOT / "kernel" / name for name in
             ("trim.fragment", "znlite.fragment", "features.fragment", "platform.fragment")]
ASSIGNMENT = re.compile(r'^(CONFIG_[A-Za-z0-9_]+)=(y|m|n|[0-9]+|0x[0-9a-fA-F]+|"[^"\n]*")$')
DISABLED = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
SYMBOL = re.compile(r"^\s*(?:menu)?config\s+([A-Za-z0-9_]+)\s*$", re.MULTILINE)


def parse_config(path):
    values = {}
    for number, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        match = DISABLED.fullmatch(line)
        if match:
            key, value = match[1], "n"
        else:
            match = ASSIGNMENT.fullmatch(line)
            if match:
                key, value = match.groups()
            elif line.startswith("# CONFIG_"):
                raise ValueError(f"{path}:{number}: malformed disabled assignment: {line}")
            elif not line or line.startswith("#"):
                continue
            else:
                raise ValueError(f"{path}:{number}: invalid Kconfig assignment: {line}")
        if key in values:
            raise ValueError(f"{path}:{number}: duplicate {key}")
        values[key] = value
    return values


def load_policy(paths):
    policy = {}
    for path in paths:
        values = parse_config(path)
        overlap = policy.keys() & values.keys()
        if overlap:
            raise ValueError(f"{path}: repeated policy symbols: {', '.join(sorted(overlap))}")
        policy.update(values)
    return policy


def compare(policy, actual):
    return [{"symbol": key, "expected": value, "actual": actual.get(key, "n")}
            for key, value in sorted(policy.items()) if actual.get(key, "n") != value]


def defined_symbols(source):
    symbols = set()
    for path in source.rglob("Kconfig*"):
        if path.is_file():
            symbols.update("CONFIG_" + name for name in
                           SYMBOL.findall(path.read_text(errors="replace")))
    if not symbols:
        raise ValueError(f"No upstream Kconfig definitions found under {source}")
    return symbols


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--lint", action="store_true")
    args = parser.parse_args(argv)
    if not args.config and not args.lint:
        parser.error("specify --config or --lint")
    try:
        policy = load_policy(FRAGMENTS)
        unknown = sorted(policy.keys() - defined_symbols(args.source)) if args.source else []
        actual = parse_config(args.config) if args.config else {}
        mismatches = compare(policy, actual) if args.config else []
        report = {
            "passed": not (mismatches or unknown),
            "requested_symbols": len(policy),
            "resolved_config_checked": bool(args.config),
            "source_symbols_checked": bool(args.source),
            "resolved_builtins": sum(value == "y" for value in actual.values()),
            "resolved_modules": sum(value == "m" for value in actual.values()),
            "unknown_symbols": unknown,
            "mismatches": mismatches,
            "source_lock": (ROOT / "kernel/source.lock").read_text().splitlines(),
        }
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + "\n")
        for symbol in unknown:
            print(f"Unknown upstream Kconfig symbol: {symbol}", file=sys.stderr)
        for item in mismatches:
            print(f"{item['symbol']}: requested {item['expected']}, resolved {item['actual']}",
                  file=sys.stderr)
        if args.config:
            print(f"Kernel policy: {len(policy)} settings; "
                  f"{len(mismatches)} mismatches; {len(unknown)} unknown symbols.")
        else:
            print(f"Kernel policy lint: {len(policy)} well-formed, non-conflicting settings.")
        return 0 if report["passed"] else 1
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
