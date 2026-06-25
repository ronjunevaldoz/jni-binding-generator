#!/usr/bin/env python3
"""
JNI Binding Generator

Generates C++ JNI boilerplate from Kotlin external function declarations.

Usage:
    python3 jni-binding-generator.py --kotlin-source <path> --output <path>

Status: Template (to be implemented in Phase 1)
"""

import argparse
import sys
from pathlib import Path


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate C++ JNI bindings from Kotlin external functions"
    )
    parser.add_argument(
        "--kotlin-source",
        required=True,
        help="Path to Kotlin source directory (e.g., core/llama/src/jvmMain)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for generated C++ files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing files",
    )
    return parser.parse_args()


class KotlinFunctionParser:
    """Parses Kotlin external fun declarations."""

    def __init__(self):
        pass

    def parse_external_functions(self, kotlin_file: str):
        """Extract external fun declarations from Kotlin file."""
        # TODO: Implement in Phase 1
        pass


class CppJniStubGenerator:
    """Generates C++ JNI stubs."""

    def __init__(self):
        pass

    def generate_marshalling(self, func):
        """Generate marshalling code for a function."""
        # TODO: Implement in Phase 1
        pass

    def generate_struct_population(self, func):
        """Generate struct population code."""
        # TODO: Implement in Phase 1
        pass

    def generate_error_handling(self, func):
        """Generate error handling code."""
        # TODO: Implement in Phase 1
        pass


def main():
    """Main entry point."""
    args = parse_args()

    kotlin_source = Path(args.kotlin_source)
    output_dir = Path(args.output)

    if not kotlin_source.exists():
        print(f"Error: Kotlin source path does not exist: {kotlin_source}", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Kotlin source: {kotlin_source}")
    print(f"Output: {output_dir}")
    print("[Phase 0 template] Implementation pending Phase 1")

    # TODO: Phase 1 implementation
    # 1. Find all .kt files in kotlin_source
    # 2. Parse external fun declarations
    # 3. Generate C++ JNI stubs
    # 4. Write to output_dir


if __name__ == "__main__":
    main()
