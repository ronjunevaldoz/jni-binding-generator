from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _generator import generate_file, generate_test_file, output_basename, test_output_basename
from _ios import generate_ios_cinterop_files
from _models import EXIT_DRIFT, EXIT_OK, EXIT_PARSE, EXIT_USAGE, ParsedFile
from _parser import parse_kotlin_file
from _types import UnknownTypeError, load_type_map


def collect_kotlin_files(source: Path) -> list[Path]:
    if source.is_file():
        return [source] if source.suffix == ".kt" else []
    return sorted(source.rglob("*.kt"))


def run(
    kotlin_source: Path,
    output_dir: Path,
    dry_run: bool,
    check: bool,
    generate_tests: bool = False,
    diff: bool = False,
    verbose: bool = False,
    package_filter: str = "",
) -> int:
    files = collect_kotlin_files(kotlin_source)
    if not files:
        print(f"No .kt files found under {kotlin_source}", file=sys.stderr)
        return EXIT_USAGE

    # Pre-pass: parse every file so we can detect class-name collisions before
    # choosing output names.  A single .kt may yield multiple ParsedFiles when
    # it contains more than one top-level class/object.
    parsed_files: list[tuple[Path, ParsedFile]] = []
    for kt in files:
        try:
            for parsed in parse_kotlin_file(kt):
                if not parsed.functions:
                    continue
                if package_filter and not parsed.package.startswith(package_filter):
                    if verbose:
                        print(f"[skip] {kt} (package {parsed.package!r} filtered)")
                    continue
                parsed_files.append((kt, parsed))
        except ValueError as exc:
            print(f"Error in {kt}: {exc}", file=sys.stderr)
            return EXIT_PARSE

    name_counts: dict = {}
    for _, parsed in parsed_files:
        name_counts[parsed.class_name] = name_counts.get(parsed.class_name, 0) + 1

    generated = 0  # files with external funs (work items)
    written = 0  # files actually written this run
    drifted: list[Path] = []

    for kt, parsed in parsed_files:
        if verbose:
            print(f"[gen] {parsed.class_name} ({len(parsed.functions)} fn)")
            for fn in parsed.functions:
                print(f"      {fn.name}()")
        try:
            content = generate_file(parsed, kt.name)
        except (UnknownTypeError, ValueError) as exc:
            print(f"Error in {kt}: {exc}", file=sys.stderr)
            return EXIT_PARSE

        qualified = name_counts[parsed.class_name] > 1
        out_path = output_dir / output_basename(parsed, qualified)
        existing = out_path.read_text(encoding="utf-8") if out_path.exists() else None
        up_to_date = existing == content
        generated += 1

        if check:
            status = "ok" if up_to_date else ("missing" if existing is None else "DRIFT")
            print(f"[check] {out_path}: {status}")
            if not up_to_date:
                drifted.append(out_path)
        elif diff:
            import difflib

            old_lines = existing.splitlines(keepends=True) if existing else []
            new_lines = content.splitlines(keepends=True)
            delta = list(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile=str(out_path),
                    tofile=str(out_path) + " (new)",
                )
            )
            if delta:
                print(f"--- {out_path}")
                print("".join(delta))
            else:
                print(f"{out_path}: unchanged")
        elif dry_run:
            print(f"{kt}  ->  {out_path}  ({len(parsed.functions)} fn) [dry-run]")
            print(content)
        elif up_to_date:
            print(f"{kt}  ->  {out_path}  (unchanged)")
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
            written += 1
            print(f"{kt}  ->  {out_path}  ({len(parsed.functions)} fn) [written]")

        if generate_tests and not dry_run:
            test_content = generate_test_file(parsed, kt.name)
            test_path = output_dir / test_output_basename(parsed, qualified)
            test_existing = test_path.read_text(encoding="utf-8") if test_path.exists() else None
            if check:
                test_status = (
                    "ok"
                    if test_existing == test_content
                    else "missing"
                    if test_existing is None
                    else "drift"
                )
                print(f"[check] {test_path}: {test_status}")
                if test_existing != test_content:
                    drifted.append(test_path)
            elif test_existing != test_content:
                output_dir.mkdir(parents=True, exist_ok=True)
                test_path.write_text(test_content, encoding="utf-8")
                print(f"{kt}  ->  {test_path}  [test written]")
            else:
                print(f"{kt}  ->  {test_path}  (test unchanged)")

    if generated == 0:
        print("No external functions found; nothing generated.", file=sys.stderr)
        return EXIT_USAGE

    if check:
        if drifted:
            print(
                f"\n{len(drifted)} generated file(s) are out of date. "
                f"Run the generator and commit the result.",
                file=sys.stderr,
            )
            return EXIT_DRIFT
        print(f"\nAll {generated} generated file(s) are up to date.")
        return EXIT_OK

    if dry_run:
        return EXIT_OK
    print(f"Done. {written} written, {generated - written} unchanged.")
    return EXIT_OK


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate C++ JNI bindings from Kotlin external functions"
    )
    parser.add_argument(
        "--kotlin-source",
        required=True,
        help="Path to a Kotlin file or source directory (scanned recursively)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for generated C++ files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated code without writing files",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify generated files are up to date without writing; "
        "exit 3 on drift (for CI / pre-commit)",
    )
    parser.add_argument(
        "--generate-tests",
        action="store_true",
        help="Also emit a *_jni_test.gen.cpp compile-time type-check file alongside each binding",
    )
    parser.add_argument(
        "--type-map",
        metavar="FILE",
        help="JSON file with custom Kotlin→JNI type mappings to merge before generation",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Print a unified diff of what would change without writing files",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print per-class and per-function progress",
    )
    parser.add_argument(
        "--package-filter",
        metavar="PKG",
        default="",
        help="Only process source files whose package starts with PKG",
    )
    parser.add_argument(
        "--ios-cinterop",
        metavar="DIR",
        help="Also generate a Kotlin/Native cinterop .def + C header skeleton in DIR",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.type_map:
        type_map_path = Path(args.type_map)
        if not type_map_path.exists():
            print(f"Error: --type-map file not found: {type_map_path}", file=sys.stderr)
            return EXIT_USAGE
        try:
            load_type_map(type_map_path)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return EXIT_USAGE
    kotlin_source = Path(args.kotlin_source)
    if not kotlin_source.exists():
        print(f"Error: Kotlin source path does not exist: {kotlin_source}", file=sys.stderr)
        return EXIT_USAGE
    rc = run(
        kotlin_source,
        Path(args.output),
        args.dry_run,
        args.check,
        args.generate_tests,
        args.diff,
        args.verbose,
        args.package_filter,
    )
    if rc != EXIT_OK:
        return rc

    if args.ios_cinterop and not args.check and not args.dry_run:
        # Re-collect parsed files (respecting the same package filter) for cinterop output.
        cinterop_files: list[tuple[Path, ParsedFile]] = []
        for kt in collect_kotlin_files(kotlin_source):
            try:
                for parsed in parse_kotlin_file(kt):
                    if not parsed.functions:
                        continue
                    if args.package_filter and not parsed.package.startswith(args.package_filter):
                        continue
                    cinterop_files.append((kt, parsed))
            except ValueError:
                pass
        if cinterop_files:
            generate_ios_cinterop_files(cinterop_files, Path(args.ios_cinterop))

    return EXIT_OK
