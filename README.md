# JNI Binding Generator

Automate boilerplate code generation for JNI (Java Native Interface) bindings from Kotlin to C++.

## Quick Summary

**Problem:** Adding new native C++ bindings via JNI requires hand-writing 100+ lines of repetitive marshalling code (string conversion, array unpacking, struct population, error handling).

**Solution:** A Python script that reads your Kotlin `external fun` declarations and generates corresponding C++ JNI stubs, reducing boilerplate by 60–80%.

## Status

✅ **Fully implemented.** The generator parses Kotlin `external fun` declarations
and emits compiling C++ JNI stubs with full type support, Gradle integration,
incremental writes, drift detection, and comprehensive docs.

| Area | Detail |
|---|---|
| **Type coverage** | All Kotlin primitives, `String`, all `*Array` variants, `List<T>`, `Set<T>`, `Map<K,V>`, nested collections, enums |
| **Tests** | 137 unit tests across 5 suites + compile-check integration test against real JDK headers |
| **Docs** | [Type matrix](docs/type-support-matrix.md) · [Memory management](docs/memory-management.md) · [Unit testing](docs/unit-testing.md) · [Advanced usage](docs/advanced-usage.md) |
| **CI / hooks** | Pre-commit: ruff lint + unit tests + drift check |
| **Gradle** | Raw `Exec` task or typed `jniGenerator { bindings { ... } }` convention plugin |

## Try It

```bash
# Generate C++ JNI stubs from the sample Kotlin binding
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/sample-binding/SampleEngine.kt \
    --output examples/sample-binding/generated

# Also emit a compile-time type-check file (*_jni_test.gen.cpp) alongside each binding
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/sample-binding/SampleEngine.kt \
    --output examples/sample-binding/generated \
    --generate-tests

# Preview what would change without writing (unified diff)
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/sample-binding/SampleEngine.kt \
    --output examples/sample-binding/generated \
    --diff

# Load custom Kotlin→JNI type mappings from a JSON file
python3 scripts/jni-binding-generator.py \
    --kotlin-source src/ \
    --output generated/ \
    --type-map my-types.json

# Filter to a specific package (e.g., in a KMP project with mixed sources)
python3 scripts/jni-binding-generator.py \
    --kotlin-source shared/src/androidMain/kotlin \
    --output androidApp/src/main/cpp/generated \
    --package-filter com.example.myapp

# Also generate a Kotlin/Native cinterop .def + C header skeleton for iOS
python3 scripts/jni-binding-generator.py \
    --kotlin-source shared/src/androidMain/kotlin \
    --output androidApp/src/main/cpp/generated \
    --ios-cinterop iosApp/src/nativeInterop/cinterop

# Show per-function generation progress
python3 scripts/jni-binding-generator.py \
    --kotlin-source src/ \
    --output generated/ \
    --verbose

# Run the test suite (unit + integration compile test)
python3 -m pytest scripts/tests/

# CI / pre-commit: verify committed output is up to date (exits non-zero on drift)
python3 scripts/jni-binding-generator.py \
    --kotlin-source examples/sample-binding/SampleEngine.kt \
    --output examples/sample-binding/generated \
    --check

# Install via pip (then use from anywhere as `jni-binding-generator`)
pip install .
```

Writes are incremental (unchanged files keep their mtime), and a GitHub Actions
workflow plus a `.pre-commit-config.yaml` run the tests and a drift check.

## Kotlin Multiplatform (KMP) Support

The generator integrates cleanly into KMP projects. JNI is used for Android and JVM Desktop targets; iOS uses Kotlin/Native cinterop (out of scope for JNI generation).

```
shared/src/
  androidMain/NativeBridgeJni.kt  ← external fun declarations (generator input)
  desktopMain/NativeBridgeJni.kt  ← same for JVM Desktop
  iosMain/NativeBridge.ios.kt     ← Kotlin/Native cinterop (not processed)
  commonMain/NativeBridge.kt      ← expect class (not processed)
```

Wire it in `shared/build.gradle.kts`:

```kotlin
tasks.register<Exec>("generateJniAndroid") {
    commandLine("python3", "scripts/jni-binding-generator.py",
        "--kotlin-source", "shared/src/androidMain/kotlin",
        "--output", "androidApp/src/main/cpp/generated")
}
tasks.named("preBuild") { dependsOn("generateJniAndroid") }
```

Use `--ios-cinterop DIR` to generate a `.def` + C header skeleton alongside the JNI output:

```bash
python3 scripts/jni-binding-generator.py \
    --kotlin-source shared/src/androidMain/kotlin \
    --output androidApp/src/main/cpp/generated \
    --ios-cinterop iosApp/src/nativeInterop/cinterop
```

See [`examples/kmp-binding/`](examples/kmp-binding/) for a complete working example.

## What This Is

- **Python-based code generator** — Parses Kotlin external functions, emits C++ JNI stubs
- **KMP-aware** — Works with `androidMain` and `desktopMain` source sets; `--ios-cinterop` generates `.def` skeletons
- **pip-installable** — `pip install .` adds a `jni-binding-generator` CLI command
- **Optional Gradle integration** — One-line task to regenerate when Kotlin interfaces change
- **Claude agent skill** — Interactive refinement via `/jni-binding-generator` agent
- **Generic template** — Works with any Kotlin/JNI project (not tied to a specific organization or library)

## Use Cases

- Adding a new native C++ inference engine to a Kotlin app
- Binding an existing C++ library to Kotlin via JNI
- Reducing manual JNI boilerplate across multiple bindings
- Enabling non-C++ developers to safely add native code

## Example

**Input (Kotlin):**
```kotlin
external fun nativeProcess(
    handle: Long,
    input: String,
    timeout: Int
): ByteArray?
```

**Generated (C++):**
```cpp
// Marshalling
std::string input_str = jstring2string(env, input);
int timeout_val = static_cast<int>(timeout);

// Struct population
process_config_t cfg{};
cfg.input = input_str.c_str();
cfg.timeout = timeout_val;

// Error handling
if (!handle) {
    throw_illegal_state(env, "nativeProcess: handle not initialized");
    return nullptr;
}
```

## Repository Structure

```
jni-binding-generator/
├── README.md                           # This file
├── LICENSE                             # Apache 2.0
├── ruff.toml                           # Python linter config (ruff)
├── .pre-commit-config.yaml             # Pre-commit: ruff + tests + drift check
├── docs/
│   ├── JNI_BINDING_GENERATOR_PLAN.md   # Full project plan & decision framework
│   ├── type-support-matrix.md          # All supported Kotlin types (param/return status)
│   ├── memory-management.md            # Local-ref contract, make_* ownership, global refs
│   ├── unit-testing.md                 # Test suites, how to add tests, exit codes
│   └── advanced-usage.md               # Thread safety, JNI_OnLoad, exceptions, NDK
├── scripts/
│   ├── jni-binding-generator.py        # Core generator
│   ├── jni-utils.h                     # C++ marshalling/exception helpers (header-only)
│   └── tests/
│       ├── test_parser.py              # Parser + JNI name-mangling tests
│       ├── test_generator.py           # Code-generation + compile-check tests
│       ├── test_driver.py              # CLI driver: incremental writes, --check, --generate-tests
│       ├── test_memory.py              # Static-analysis: local-ref lifecycle in jni-utils.h
│       └── test_integration.py         # Compile test against real JDK headers (all types)
├── examples/
│   ├── sample-binding/                 # Reference: single-module example
│   │   ├── SampleEngine.kt
│   │   └── generated/
│   │       ├── SampleEngine_jni.gen.cpp
│   │       └── SampleEngine_jni_test.gen.cpp
│   └── kmp-binding/                    # Kotlin Multiplatform example
│       ├── shared/src/
│       │   ├── commonMain/  NativeBridge.kt         (expect class)
│       │   ├── androidMain/ NativeBridgeJni.kt      (external fun → JNI)
│       │   ├── iosMain/     NativeBridge.ios.kt     (Kotlin/Native cinterop stub)
│       │   └── desktopMain/ NativeBridgeJni.kt      (external fun → JNI)
│       ├── androidApp/src/main/cpp/generated/       (generated JNI bindings)
│       └── desktopApp/src/jvmMain/cpp/generated/    (generated JNI bindings)
├── gradle-integration/                 # Run the generator from Gradle
│   ├── README.md                       # Raw-task and convention-plugin options
│   └── build-logic/                    # Precompiled `id("jni-generator")` plugin
├── pyproject.toml                      # pip-installable: pip install .
└── .gitignore
```

## Quick Facts

| Aspect | Detail |
|---|---|
| **Language** | Python 3.9+ (generator) · C++ header-only helpers · optional Kotlin (Gradle DSL) |
| **Dependencies** | None at runtime — stdlib only; `ruff` for linting; `pre-commit` for hooks |
| **ROI break-even** | ~4th binding (saves ~2 hrs of hand-written boilerplate per new binding) |
| **Original plan** | [PLAN.md](docs/JNI_BINDING_GENERATOR_PLAN.md) — phases 0–3 and decision framework |

## Credits & Attribution

This project is inspired by **[awake-vulkan-generator](https://github.com/ronjunevaldoz/awake/tree/vulkan/awake-vulkan-generator)** — a working code generator that automatically converts Kotlin/JVM bindings to C++ JNI boilerplate for the Vulkan graphics library.

**Key insight:** The awake-vulkan-generator proved that this approach works in production. It solved the exact problem we're generalizing here — eliminating 200+ lines of hand-written JNI marshalling code across multiple native bindings.

### How This Project Came Together

This project was created with **AI assistance (Claude)** to:
1. Analyze the patterns in awake-vulkan-generator
2. Generalize the approach for any JNI binding
3. Plan a reusable, open-source tool
4. Document the architecture and decision framework

**Why it matters:** Building a generator manually takes weeks of trial-and-error. With AI, we went from a working reference implementation to a generic, well-documented plan in days — proving that AI can accelerate developer tools creation.

## Contact & Feedback

This project is a template ready for evaluation.  
Share feedback or questions in issues (when repo is live).

---

**Owner:** Ron Valdoz  
**Reference:** [awake-vulkan-generator](https://github.com/ronjunevaldoz/awake/tree/vulkan/awake-vulkan-generator)  
**License:** Apache 2.0
