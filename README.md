# JNI Binding Generator

Automate boilerplate code generation for JNI (Java Native Interface) bindings from Kotlin to C++.

## Quick Summary

**Problem:** Adding new native C++ bindings via JNI requires hand-writing 100+ lines of repetitive marshalling code (string conversion, array unpacking, struct population, error handling).

**Solution:** A Python script that reads your Kotlin `external fun` declarations and generates corresponding C++ JNI stubs, reducing boilerplate by 60–80%.

## Status

📋 **Planning phase** — Project plan ready for review and decision.

See [PLAN.md](docs/JNI_BINDING_GENERATOR_PLAN.md) for full details.

## What This Is

- **Python-based code generator** — Parses Kotlin external functions, emits C++ JNI stubs
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
├── docs/
│   └── JNI_BINDING_GENERATOR_PLAN.md   # Full project plan & decision framework
├── scripts/
│   ├── jni-binding-generator.py        # Core generator (to be implemented)
│   ├── jni-utils.h                     # C++ helper snippets
│   └── tests/
│       ├── test_parser.py
│       └── test_generator.py
├── examples/
│   └── sample-binding/                 # Reference: before & after
└── .gitignore
```

## Decision & Next Steps

**Question:** Should we build this?

👉 **Read [PLAN.md](docs/JNI_BINDING_GENERATOR_PLAN.md)** to:
1. Understand the problem and proposed solution
2. Review implementation phases (3–4 weeks)
3. Answer 5 decision questions
4. See when parking is recommended vs proceeding

## Quick Facts

| Aspect | Detail |
|---|---|
| **Estimated effort (MVP)** | 3 weeks (9–13 days) |
| **Language** | Python 3.9+ (core) + optional Kotlin (Gradle wrapper) |
| **First decision gate** | After Phase 0 (agent skill, 2–3 days) |
| **ROI break-even** | Adding binding #4 (saves ~2 hours per new binding after initial investment) |
| **Publishing** | Deferred to Phase 2+ (local integration first) |

## Contact & Feedback

This project is a template ready for evaluation.  
Share feedback or questions in issues (when repo is live).

---

**Status:** Awaiting decision to proceed or park.  
**Owner:** Ron Valdoz  
**License:** Apache 2.0
