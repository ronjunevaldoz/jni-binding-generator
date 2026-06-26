# JNI Binding Generator — Project Plan

**Status:** Generic planning template — adaptable to any JNI binding scenario.

> **Note:** This plan was developed using graphyn (multiplatform inference engine) as a reference example, but is designed to be **project-agnostic**. Apply these phases and trade-offs to your own Kotlin/JNI project by substituting your engine names, module paths, and native library specifics.

## Executive Summary

**Proposal:** Build a code generator to automate JNI boilerplate for native C++ libraries bound via JNI (e.g., inference engines, image processing, audio codecs, or any structured C++ API with 3+ bindings).

**Status:** Phase 1 (Python generator) implemented and tested. The generator parses Kotlin `external fun` declarations and emits C++ JNI stubs that compile against the JDK's JNI headers. See [`scripts/jni-binding-generator.py`](../scripts/jni-binding-generator.py) and the worked example in [`examples/sample-binding/`](../examples/sample-binding/). Phases 2–3 (Gradle integration, hardening) remain optional/future work.

**Estimated effort:** 3–4 weeks (agent skill + Python script + Gradle integration).

**ROI:** High if adding 4+ bindings; marginal if staying with 3 long-term.

---

## Problem Statement

### Current Pain Points (Your Scenario)

1. **Boilerplate duplication:** Each new native binding adds 100–150 lines of hand-written C++ JNI stubs.
   - String marshalling: `jstring2string(env, xyz)` copied 6+ times per binding
   - Array unpacking: 20+ lines per array type (String[], float[], custom types)
   - Request/config struct population: identical field-by-field assignment patterns
   - Error handling: standardized but repetitive (try-catch, exception throwing)

2. **Error-prone manual work:** Missing a field in struct population, incorrect array bounds check, forgotten `DeleteLocalRef` calls, memory leaks in exception paths.

3. **Knowledge barrier:** Adding a new binding requires C++ expertise + JNI knowledge (not just Kotlin). Developers can't confidently write JNI without template examples.

### Current Scope (Your Project)

Example: You have 3 native libraries bound via JNI:
- **Library A** (core functionality): 3 external functions, ~50 lines C++ JNI
- **Library B** (complex with arrays): 3 external functions, ~220 lines C++ JNI
- **Library C** (simple interface): 1 external function, ~50 lines C++ JNI

**Total hand-written:** ~320 lines across 3 bindings.

> *Replace A/B/C with your actual library names (e.g., llama.cpp, stable-diffusion.cpp, etc.)*

---

## Objectives

### Primary Goals

1. **Reduce JNI boilerplate by 60–80%** — auto-generate marshalling, struct population, error handling for all bindings.
2. **Enable non-C++ developers to add bindings** — provide a clear tool so Java/Kotlin developers can spec new native bindings without deep C++/JNI expertise.
3. **Improve consistency** — all bindings follow identical error handling, array unpacking, callback patterns (not one-off implementations).
4. **Maintain hand-written flexibility** — progress callbacks, custom memory management, edge cases remain manual (not templated).

### Success Criteria

- ✅ Generated C++ compiles and passes existing test suite for all 3 engines
- ✅ Generation time < 1s per engine
- ✅ New engine can be added with < 50 lines hand-written C++ (only custom logic)
- ✅ Agent skill (`/jni-binding-generator`) and Python script both functional
- ✅ Gradle task integrates cleanly; optional (not blocking builds if skipped)

---

## Architecture & Design

### High-Level Flow

```
Kotlin Interface Definition
  ↓ (read)
External Fun Declarations
  ↓ (parse Kotlin AST)
Generator (Python script)
  ↓ (infer types, patterns)
Generated C++ JNI Stubs
  + Manual C++ (callbacks, custom logic)
  ↓ (compile via CMake)
Linked Native Library (.dylib/.so/.dll)
```

### Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| Generator logic | Python 3.9+ | Matches existing scripts (release.py, audit); easy AST parsing |
| Parsing | Regex + manual AST walk | Kotlin `external fun` signatures are simple; no full compiler needed |
| Build integration | Gradle task (precompiled plugin) | Fits existing build-logic, optional (doesn't block native build) |
| Agent interface | Claude agent skill | Enables CLI like `/jni-binding-generator` for interactive refinement |

### Directory Structure (Template)

```
<your-project>/
├── scripts/
│   ├── jni-binding-generator.py          # Core generator (Python)
│   │   ├── KotlinFunctionParser
│   │   ├── CppJniStubGenerator
│   │   ├── MarshallingGenerator
│   │   └── TypeMapper
│   ├── jni-templates/                    # Reusable C++ templates
│   │   ├── marshalling.cpp.j2
│   │   ├── request_struct.cpp.j2
│   │   └── error_handling.h
│   └── tests/
│       ├── test_parser.py
│       └── test_generator.py
│
├── build-logic/convention/src/main/kotlin/
│   └── <your-org>.jni.generator.gradle.kts  # Gradle task wrapper
│
├── <native-module>/jni/
│   ├── manual/                           # Hand-written logic
│   │   ├── <library-a>-jni.cpp           # Custom callbacks, memory mgmt
│   │   ├── <library-b>-jni.cpp
│   │   └── <library-c>-jni.cpp
│   ├── generated/                        # Auto-generated (git-ignored)
│   │   ├── <library-a>-marshalling.hpp
│   │   ├── <library-b>-marshalling.hpp
│   │   └── <library-c>-marshalling.hpp
│   └── CMakeLists.txt                    # Includes both manual + generated
│
└── docs/
    └── JNI_BINDING_GENERATOR_PLAN.md     # This plan (template)
```

**Legend:**
- `<your-project>` — Your Kotlin Multiplatform project root
- `<your-org>` — Your organization ID (e.g., `com.example.myapp`)
- `<native-module>` — Your native module (e.g., `:core:native`, `:native`, etc.)
- `<library-a/b/c>` — Your actual library names (e.g., `llama`, `sd`, `qwen3`, etc.)

### Code Generation Strategy

#### Phase 1: Marshalling Boilerplate (80% of benefit)

**Input Kotlin (example):**
```kotlin
external fun nativeProcessData(
    handle: Long,
    input: String,
    timeout: Int,
    threshold: Float,
    flags: Long,
): ByteArray?
```

**Generated C++ (example):**
```cpp
// Extracted from JNI stub
std::string input_str = jstring2string(env, input);
int timeout_val = static_cast<int>(timeout);
float threshold_val = static_cast<float>(threshold);
long flags_val = static_cast<long>(flags);
```

**Handling:**
- Primitive (jint, jfloat, jlong) → direct cast
- String (jstring) → utility function (e.g., `jstring2string()`)
- Arrays (jobjectArray, jfloatArray) → vector unpacking
- Custom types → predefined mappings (user-configurable)

#### Phase 2: Request Struct Population (10% of benefit)

**Input Kotlin (example):**
```kotlin
external fun nativeDoWork(
    context: Long,
    configPath: String,
    mode: String,
): ByteArray?
```

**Generated C++ (example):**
```cpp
work_config_t cfg{};
cfg.context_path = context_path_str.c_str();
cfg.mode         = mode_str.c_str();
```

**Naming convention:** The generator infers struct name from function name; user can override.

#### Phase 3: Error Handling Standardization (5% of benefit)

**Generated error checks (template):**
```cpp
if (!context) {
    throw_illegal_state(env, "nativeDoWork: context not initialized");
    return nullptr;
}
if (config_path_str.empty()) {
    throw_illegal_argument(env, "nativeDoWork: configPath required");
    return nullptr;
}
```

**Your patterns:** Replace `throw_illegal_*` with your own error handling (e.g., custom exception class).

---

## Implementation Phases

### Phase 0: Agent Skill Draft (Week 1)

**Goal:** Prototype generator via agent interaction.

**Tasks:**
1. Create `/jni-binding-generator` agent skill
   - Input: Path to Kotlin file with `external fun` declarations
   - Output: Generated C++ JNI stubs + marshalling headers
   - Handles: String/array marshalling, struct population, error checks

2. Test on your existing bindings:
   - Parse your first Kotlin wrapper → generate equivalent C++ marshalling
   - Parse your second wrapper → generate struct population code
   - Parse your third wrapper → test error handling patterns

3. Capture patterns from generated output:
   - What varies between your bindings?
   - What's identical (becomes reusable template)?
   - What can't be automated (custom logic)?

**Effort:** 2–3 days  
**Deliverable:** Working agent skill + pattern documentation

---

### Phase 1: Python Script Implementation (Week 2) — ✅ IMPLEMENTED

**Goal:** Convert agent-generated patterns into a production Python script.

**Status:** Done. Implemented in [`scripts/jni-binding-generator.py`](../scripts/jni-binding-generator.py) with:
- `KotlinFunctionParser` — comment-stripped regex parse of `external fun` signatures (package, class/object, params, return type, nullability, default values, generics like `Array<String>`).
- `TypeMapper` — `TYPE_MAP` / `RETURN_MAP` tables with actionable errors for unmapped types.
- `CppJniStubGenerator` — emits full `extern "C"` JNI entry points with JNI short-name mangling, argument marshalling, handle/string error checks, and a TODO body.
- C++ helpers in [`scripts/jni-utils.h`](../scripts/jni-utils.h) (`jstring2string`, `extract_*_array`, `throw_illegal_*`).
- 16 unit tests in [`scripts/tests/`](../scripts/tests/) (`python3 -m unittest discover -s scripts/tests`).
- Verified: generated output compiles against JDK 17 JNI headers via `clang++ -fsyntax-only`.

**Original task breakdown (for reference):**

**Tasks:**

1. **Build Kotlin parser** (`KotlinFunctionParser`)
   - Read Kotlin source file with `external fun` declarations
   - Extract function name, parameters (name + type), return type
   - Support types: `jstring`, `jint`, `jlong`, `jfloat`, `jboolean`, `jobjectArray`, `jfloatArray`, custom types

   ```python
   def parse_external_functions(kotlin_file: str) -> List[ExternalFunction]:
       """Regex or AST parse: external fun nativeXxx(param: jtype, ...): jreturn"""
       pass
   ```

2. **Build type mapper** (`TypeMapper`)
   - Define your Kotlin → C++ type mappings:
     - Example: `Long` → `jlong` → `void*` or `int64_t`
     - Example: `String` → `jstring` → `std::string`
     - Example: `ByteArray` → `jbyteArray` → `std::vector<uint8_t>`
   - Customize per your library's conventions

   ```python
   TYPE_MAPPING = {
       "Long": ("jlong", "static_cast<jlong>({var})"),
       "String": ("jstring", "jstring2string(env, {var})"),
       # ... your types ...
   }
   ```

3. **Build marshalling generator** (`MarshallingGenerator`)
   - For each parameter, emit C++ extraction/conversion code
   - Handle: null checks, empty string checks, array bounds

   ```python
   def generate_marshalling(func: ExternalFunction) -> str:
       """Emit: type conversions, jstring2string calls, array unpacking"""
       pass
   ```

4. **Build struct population generator** (`StructPopulationGenerator`)
   - Infer struct name from function name (user can override)
   - Map parameters to struct fields (infer field naming convention: camelCase → snake_case?)
   - Handle optional fields

5. **Build error handling generator**
   - Standard null/empty checks
   - Use your error throwing utility (replace `throw_illegal_*` with your patterns)

6. **Test suite** (`tests/`)
   - Regression tests: parse your existing JNI files, verify generated output matches
   - Compare line-by-line (ignoring whitespace)
   - Add new test for each binding you add

**Effort:** 5–7 days  
**Deliverable:** Python script + test suite, covering all your existing bindings.

---

### Phase 2: Gradle Integration (Week 3) — ✅ IMPLEMENTED (template)

**Goal:** Make generation a first-class Gradle task.

**Status:** Shipped as a copy-paste integration in [`gradle-integration/`](../gradle-integration/README.md):
- **Option A — raw `Exec` task:** zero infrastructure, paste into a module's `build.gradle.kts`. Declares Kotlin source as input / output dir as output for up-to-date checks.
- **Option B — convention plugin:** [`jni-generator.gradle.kts`](../gradle-integration/build-logic/convention/src/main/kotlin/jni-generator.gradle.kts) precompiled script plugin applied via `id("jni-generator")`, with a `jniGenerator { bindings { register("...") { ... } } }` DSL that generates one task per binding plus an aggregate.
- Lifecycle wiring (`dependsOn("generateJniBindings")`) and a CI drift-check snippet documented.
- The CLI contract the tasks depend on (directory input, non-zero exit on missing source) is verified; the Gradle Kotlin DSL files are a template (not executed here — no Gradle binary in the authoring environment).

**Original task breakdown (for reference):**

1. **Create Gradle task** (`<your-org>.jni.generator.gradle.kts` in build-logic)
   ```kotlin
   tasks.register<Exec>("generateJniBindings") {
       commandLine("python3", "${rootDir}/scripts/jni-binding-generator.py")
       args(
           "--kotlin-source", "${rootDir}/<your-binding-a>/src/jvmMain",
           "--output", "${rootDir}/<native-module>/jni/generated/<library-a>"
       )
       workingDir(rootDir)
   }
   ```

2. **Wire into build lifecycle** (optional, not blocking native build)
   ```kotlin
   // In your :native:build.gradle.kts or convention plugin
   tasks.named("buildNative") {
       dependsOn("generateJniBindings")  // Regenerate before native build
   }
   ```

3. **Add configuration DSL** (nice-to-have for multiple bindings)
   ```kotlin
   jniGenerator {
       bindings {
           libraryA {
               kotlinSource = "<your-binding-a>/src/jvmMain"
               outputDir = "<native-module>/jni/generated/<library-a>"
           }
           libraryB {
               kotlinSource = "<your-binding-b>/src/jvmMain"
               outputDir = "<native-module>/jni/generated/<library-b>"
           }
       }
   }
   ```

4. **Documentation:**
   - Add section to `<native-module>/README.md`: "Regenerating JNI Bindings"
   - Usage: `./gradlew generateJniBindings`

**Effort:** 2–3 days  
**Deliverable:** Gradle task + documentation.

---

### Phase 3: Polish & Testing (Week 4, Optional)

**Goal:** Production readiness (if pursuing implementation).

**Tasks:**

1. **Integration test** — new binding (not yet in your project):
   - Manually create a dummy Kotlin interface with 5 external functions
   - Run generator
   - Verify generated C++ compiles without errors

2. **Incremental generation** (nice-to-have):
   - Track source file modification time; regenerate only if Kotlin changed
   - Reduces re-run time from 1s to 100ms for unchanged bindings

3. **Error messages:**
   - Clear feedback if parser fails ("Line 42: unrecognized type `CustomStruct`")
   - Suggestions for fixing (e.g., "add type mapping in config")

4. **CI integration** (optional):
   - Pre-commit hook: `pre-commit run jni-binding-generator`
   - CI job: verify generated code matches committed code (catch manual edits)

**Effort:** 3–4 days  
**Deliverable:** Hardened script, CI-ready.

---

## Timeline & Effort

| Phase | Duration | Effort | Gate |
|---|---|---|---|
| **Phase 0: Agent Skill** | Week 1 | 2–3 days | Decision gate: proceed? |
| **Phase 1: Python Script** | Week 2 | 5–7 days | Regression tests pass |
| **Phase 2: Gradle Integration** | Week 3 | 2–3 days | Task runs cleanly |
| **Phase 3: Polish** | Week 4 (opt) | 3–4 days | Production ready |
| **Total (MVP)** | **3 weeks** | **9–13 days** | |
| **Total (Hardened)** | **4 weeks** | **12–17 days** | |

---

## Trade-offs & Risks

### Trade-off: Python Script vs Gradle Plugin

| Aspect | Python Script | Gradle Plugin |
|---|---|---|
| **Coupling** | Loose (standalone executable) | Tight (build lifecycle) |
| **Debugging** | Easy (print statements, run locally) | Harder (Gradle task model) |
| **CI/CD** | Call via `exec` task or pre-commit hook | Automatic via task dependencies |
| **Team onboarding** | "Run `python3 scripts/jni-binding-generator.py`" | "Run `./gradlew :native:generateJniBindings`" |

**Decision:** Start with Python script; migrate to plugin if team wants automation.

---

### Risk: Pattern Coverage

**Risk:** Generator doesn't handle edge cases (custom types, nested structs, callbacks).

**Mitigation:**
1. Phase 0 (agent skill) surfaces edge cases early
2. Hand-written escape hatch: generated code is always *additive*, never *required*
   - If generator breaks on a new engine, write that function by hand; others use generator
3. Fallback: generator outputs a stub; dev fills in details

**Likelihood:** Medium (agent skill testing + regression suite mitigates)

---

### Risk: Maintenance Burden

**Risk:** Generator becomes stale as Kotlin/C++ conventions evolve.

**Mitigation:**
1. Regression tests prevent silent breakage
2. Agent skill re-runs generator; if output drifts, agent catches it
3. Clear documentation of patterns (what the script assumes about struct naming, error handling)
4. Decision gate: if adding engine #6 requires significant script changes, convert to plugin or to KSP-based approach

**Likelihood:** Low (first 4 engines should be similar enough)

---

## Dependencies & Constraints

### Hard Dependencies

- Python 3.9+ (already available in repo environment)
- Existing Kotlin interfaces must follow convention: `external fun nativeXxx(...): jreturnType`
- C++ structs must follow naming: `xxxxx_request_t` for request structs
- CMakeLists.txt must be updated manually to include generated `.hpp` files

### Soft Dependencies

- Agent skill runs locally; no external API calls (uses Claude API, already available)
- Gradle 7.0+ (already in use)

### Constraints

- **Cannot automate:** Progress callbacks, custom memory management, threading primitives
  - These require domain knowledge; marked as "manual" in generated files
- **Output is not committed to git** — generated files go to `.gitignore`
  - Regenerate as part of build (like protobuf, or optional task)

---

## Success Metrics

### Short-term (MVP)

1. ✅ Generated C++ for 3 existing engines compiles without error
2. ✅ Generated code matches hand-written code within 95% (allowing for formatting differences)
3. ✅ Agent skill produces usable output for new engine spec

### Medium-term (Production)

1. ✅ Adding a 4th engine takes < 2 hours (spec + test + commit)
2. ✅ Zero hand-written JNI boilerplate (all in generated files)
3. ✅ Team runs `./gradlew :native:generateJniBindings` without thinking

### Long-term (Optional)

1. ✅ 5+ engines using same generator infrastructure
2. ✅ External teams use generator (shared as library or published script)
3. ✅ Pre-commit hook prevents drift (generated ≠ committed)

---

## Decision Gates

### Gate 1: After Phase 0 (Agent Skill)
**Question:** Does the generated C++ code look production-ready?

**Options:**
- ✅ Proceed to Phase 1 (Python script)
- ⏸️ Park (use agent skill as one-off tool, no formal integration)
- 🔄 Iterate (refine patterns, extend to handle more cases)

**Criteria for Go:**
- Generated code compiles for at least 2 of 3 existing engines
- No undefined behavior or memory leaks in generated marshalling
- Developer time to integrate into project < 4 hours

---

### Gate 2: After Phase 1 (Python Script)
**Question:** Is the Python script stable enough for team use?

**Options:**
- ✅ Proceed to Phase 2 (Gradle integration)
- ⏸️ Park (keep as optional utility; document in README)
- 🔄 Iterate (fix edge cases, improve error messages)

**Criteria for Go:**
- Regression tests pass (generated ≈ hand-written)
- Handles all 3 engines without manual intervention
- No subtle bugs found in 1 week of team use

---

### Gate 3: After Phase 2 (Gradle Integration)
**Question:** Is it seamless enough to be the default workflow?

**Options:**
- ✅ Proceed to Phase 3 (hardening)
- ⏸️ Park (optional task; not required for builds)
- 🔄 Iterate (improve task messaging, add dry-run mode)

**Criteria for Go:**
- Task runs in < 2s, no spurious failures
- Developer can regenerate without breaking build (clean separation: generated vs hand-written)
- Team uses it at least 3 times without issue

---

## Alternative Approaches (Not Recommended)

### 1. Manual Checklist
**Approach:** Document the 20-step process (copy-paste marshalling, update struct, etc.)

**Pros:**
- Zero implementation cost
- Works for 3 engines

**Cons:**
- Error-prone (humans skip steps)
- Doesn't scale beyond 5 engines
- Doesn't reduce knowledge barrier

**Recommendation:** Too low-tech; falls apart as team grows.

---

### 2. KSP-based Kotlin Plugin
**Approach:** Annotation processor generates C++ stubs during `kotlinCompile`

```kotlin
@GenerateJniBinding
external fun nativeXxx(...): jreturnType
```

**Pros:**
- Runs automatically with Kotlin compilation
- Fully typed (no regex parsing)

**Cons:**
- Complex setup (KSP plugin, custom compiler)
- Tight coupling to Kotlin compiler version
- Steep learning curve (KSP not widely known)
- Does not help with C++ side (still hand-written)

**Recommendation:** Overkill for this problem. Start simpler.

---

### 3. Codegen Macro in build-logic Plugin
**Approach:** Gradle plugin written in Kotlin, embeds generator logic

**Pros:**
- Type-safe task config
- Fully integrated with Gradle

**Cons:**
- More complex than Python script
- Harder to debug
- Slower iteration (recompile plugin to test)

**Recommendation:** Save for Phase 3 if script proves too fragile.

---

## Parking Criteria

### Reasons to Park (and Not Implement)

1. **Team size remains small (≤ 3 developers):** Overhead of building generator > benefit of saved dev hours
2. **No new bindings planned:** If your 3–4 bindings are final, generator ROI is < 1 week
3. **C++ expertise available:** If your team enjoys JNI work and understands the patterns, generator may reduce "learning by doing"
4. **Build speed not a constraint:** If native builds are fast and no one complains about regeneration, low priority
5. **Bindings diverge significantly:** If each binding uses custom error handling, struct naming, or conventions, generator patterns won't generalize well

### Decision Matrix

| Your Scenario | Recommendation |
|---|---|
| 3 bindings, stable APIs, strong C++ engineer on team | **Park** — use agent skill for occasional help |
| 3 bindings + 1–2 new planned, team lacks C++ depth | **Proceed Phase 1** — Python script only (3 weeks) |
| 5+ bindings planned, team scaling, automated builds critical | **Proceed Phase 1–3** — Full Gradle integration |
| New engine every month (rapid iteration) | **Proceed Phase 2–3** — Gradle task is critical |

---

## Documentation Plan

### For Your Development Team

1. **`scripts/jni-binding-generator.py`** — Inline comments explaining:
   - How parser extracts function signatures
   - Type mapping logic and how to extend it
   - Marshalling template generation
   - Error handling patterns

2. **`<native-module>/README.md`** — Section: "Regenerating JNI Bindings"
   ```markdown
   ## Generating JNI Bindings
   
   To regenerate marshalling code:
   
   ```bash
   ./gradlew generateJniBindings    # Via Gradle (recommended)
   
   # Or manually (for debugging):
   python3 scripts/jni-binding-generator.py \
     --kotlin-source <your-binding>/src/jvmMain \
     --output <native-module>/jni/generated
   ```
   ```

3. **`docs/JNI_BINDING_CONVENTIONS.md`** — Document your conventions:
   - Kotlin naming: external function names (e.g., `nativeXxx`)
   - C++ struct naming (e.g., `xxx_request_t`, `xxx_result_t`)
   - Error handling style (which exceptions, error codes)
   - Type mappings (how your types map to JNI types)

### For New Binding Contributors

1. **Checklist: "Adding a New Binding"**
   - Step 1: Define Kotlin `external fun` declarations in wrapper class
   - Step 2: Run generator (`./gradlew generateJniBindings`)
   - Step 3: Write hand-crafted logic (callbacks, custom memory management, edge cases)
   - Step 4: Integrate generated + manual files into CMakeLists.txt
   - Step 5: Verify generated C++ compiles

---

## Publishing (Deferred Decision)

**Don't decide publishing now.** Build and validate first (Phases 0–2), then decide based on:

### Publishing Options (Decide Later)

| Scope | Option | When |
|---|---|---|
| **Internal only** | Local convention plugin (copy-paste to projects) | Phase 1 |
| **Multiple internal projects** | GitHub Packages or Maven Central | Phase 2 (after 2–4 weeks of use) |
| **Public/external users** | Gradle Plugin Portal | Phase 3+ (after external validation) |

**Group ID:** Defer this decision until Phase 2. Will be decided based on:
- Your organization structure
- Whether it's internal or public
- Your existing publishing infrastructure

**Note:** Publishing decisions are independent of the tool itself. Start with Phase 1 (local), add publishing infrastructure later if needed.

---

## Next Steps

### Immediate (Decision)

1. **Review this plan** — Does it align with your vision?
2. **Estimate: Is 3–4 weeks viable** in your roadmap?
3. **Decision: Proceed, iterate, or park?**

### If Proceeding

1. **Create agent skill** (Phase 0) — 2–3 day spike
2. **Review generated output** — Does it look production-ready?
3. **Go/no-go for Phase 1** (Python script)

### If Parking

1. **Document decision** — Link to this plan + rationale
2. **Keep agent skill as reference** — Use manually for one-off engines
3. **Revisit when:** 4th engine planned, or team grows, or build time becomes issue

---

## Appendix: Technical Reference

### Type Mappings (Full)

```python
JAVA_TO_CPP_TYPE_MAP = {
    # Primitives
    "jint": ("int32_t", "static_cast<int32_t>({var})"),
    "jlong": ("int64_t", "static_cast<int64_t>({var})"),
    "jfloat": ("float", "static_cast<float>({var})"),
    "jboolean": ("bool", "{var} ? true : false"),
    
    # Strings
    "jstring": ("std::string", "jstring2string(env, {var})"),
    
    # Arrays
    "jobjectArray": ("std::vector<std::string>", "extract_string_array(env, {var})"),
    "jfloatArray": ("std::vector<float>", "extract_float_array(env, {var})"),
    "jintArray": ("std::vector<int32_t>", "extract_int_array(env, {var})"),
    "jbyteArray": ("std::vector<uint8_t>", "extract_byte_array(env, {var})"),
    
    # Special
    "Long (handle)": ("void*", "reinterpret_cast<void*>({var})"),
}
```

### CMake Integration

```cmake
# native/CMakeLists.txt (example)

# Generated files (always regenerate before build)
file(GLOB GENERATED_JNI_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/jni/generated/*.cpp")

# Manual JNI files (hand-written, version-controlled)
set(MANUAL_JNI_SOURCES
    jni/manual/<library-a>-jni.cpp
    jni/manual/<library-b>-jni.cpp
    jni/manual/<library-c>-jni.cpp
)

# Combine
set(ALL_JNI_SOURCES ${GENERATED_JNI_SOURCES} ${MANUAL_JNI_SOURCES})

add_library(inference-jni SHARED ${ALL_JNI_SOURCES})
target_include_directories(inference-jni PRIVATE ${JNI_INCLUDE_DIRS} jni/generated)
```

---

## Questions for Decision

Before committing, honestly answer:

1. **Timeline:** Can your team spare 3–4 weeks over the next 1–2 months?
2. **Team comfort:** Will developers adopt a Python script? Does your team already use Python?
3. **Scaling:** Do you anticipate 4+ native bindings in the next 12 months?
4. **ROI calculation:** If adding a new binding manually takes 4 hours, is a 10-hour generator investment worth it?
5. **Risk appetite:** Are you comfortable introducing a new tool into your build pipeline?

**Recommendation:**
- **Park if** you answer "No" to 3+ questions (not the right time)
- **Proceed if** you answer "Yes" to at least 3 questions (good fit)

**Example decisions:**
- "No, no, no, no, yes" → **Park** — wait for better timing
- "Yes, yes, yes, no, yes" → **Proceed** — ROI might be tight, but other signals are strong
- "Yes, yes, yes, yes, yes" → **Proceed with confidence** — all signals green

---

## References & Inspiration

### Production Reference Implementation

**[awake-vulkan-generator](https://github.com/ronjunevaldoz/awake/tree/vulkan/awake-vulkan-generator)**

This project is inspired by a working code generator that solves the exact problem described here. The awake-vulkan-generator:

- **Reads:** Kotlin data classes representing Vulkan structures (50+ of them)
- **Generates:** C++ JNI conversion code, automatically
- **Saves:** 200+ lines of hand-written marshalling code per engine
- **Proves:** The pattern works in production with 3+ native bindings

**Why it matters:** Rather than theorizing about whether generators help, we have a real working example. This plan generalizes from that proven pattern.

### Technical References

- **[JNI Specification](https://docs.oracle.com/javase/8/docs/technotes/guides/jni/)** — Reference for correct JNI patterns and function signatures
- **[Kotlin Reflection](https://kotlinlang.org/docs/reflection.html)** — Used in awake-vulkan-generator for runtime introspection
- **[Gradle Plugin Development](https://docs.gradle.org/current/userguide/custom_plugins.html)** — For Phase 2 optional Gradle integration

---

## Summary Table

| Aspect | Details |
|---|---|
| **Scope** | Automate JNI marshalling boilerplate for 3–5+ native C++ bindings |
| **Effort (MVP)** | 3 weeks, 9–13 days of development |
| **Language** | Python 3.9+ (scripting language, easy to iterate) |
| **Deliverables** | Agent skill + Python script + optional Gradle integration + documentation |
| **First decision gate** | After Phase 0 (agent skill, 2–3 days) |
| **Risk of parking** | Low — agent skill alone is useful; can stop at Phase 0 without loss |
| **Success metric** | Adding a new binding takes < 2 hours (mostly automated) vs 4+ hours (manual) |
| **Next decision** | **Your call** — See decision matrix under "Parking Criteria" |

