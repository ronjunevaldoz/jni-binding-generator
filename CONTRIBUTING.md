# Contributing to JNI Binding Generator

## Project Status

The generator is **fully implemented and production-ready.** All phases (parser, code
generator, Gradle integration, iOS cinterop, CI, docs) are complete. Contributions to
extend type coverage, add examples, improve docs, or fix bugs are welcome.

## Development Setup

```bash
git clone https://github.com/ronjunevaldoz/jni-binding-generator.git
cd jni-binding-generator

# Python 3.10+ required — no extra runtime dependencies
python3 --version

# Run the full test suite
python3 -m pytest scripts/tests/

# Or with unittest discover (same tests, used by CI)
python3 -m unittest discover -s scripts/tests -v

# Lint + format check
pip install ruff
ruff check scripts/
ruff format --check scripts/
```

## Making Changes

1. Fork the repo and create a feature branch
2. Make your changes — keep them focused; one concern per PR
3. Add or update tests (`scripts/tests/`) to cover the change
4. Run the full suite and confirm all 152 tests pass
5. Run `ruff check scripts/` — no lint errors
6. If you changed `scripts/jni-binding-generator.py`, re-run the drift check:
   ```bash
   python3 scripts/jni-binding-generator.py \
       --kotlin-source examples/sample-binding/SampleEngine.kt \
       --output examples/sample-binding/generated \
       --check
   ```
7. Update `CHANGELOG.md` under `[Unreleased]`
8. Submit a pull request

## Adding a New Type

1. Add a `TypeInfo` entry to `TYPE_MAP` in `jni-binding-generator.py`
2. Add a matching return entry to `RETURN_MAP`
3. Add `extract_*` (param) and/or `make_*` (return) helpers to `scripts/jni-utils.h`
4. Add a `_MAKE_HELPER_MAP` entry pointing to the new `make_*` helper
5. Write a test in `scripts/tests/test_generator.py`
6. Update `docs/type-support-matrix.md`

## Code Style

- **Python:** ruff enforces PEP 8; run `ruff format scripts/` to auto-format
- **C++ (jni-utils.h):** follow the existing style — inline functions, `snake_case`
- **Comments:** explain *why*, not *what*; skip obvious comments

## Reporting Issues

1. Check existing issues first
2. Include: what you tried, what failed, expected behavior
3. Attach the Kotlin `external fun` declaration that caused the problem
