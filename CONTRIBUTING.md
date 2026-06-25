# Contributing to JNI Binding Generator

## Project Status

This project is in **planning phase**. See [docs/JNI_BINDING_GENERATOR_PLAN.md](docs/JNI_BINDING_GENERATOR_PLAN.md) for the full roadmap.

## How to Contribute

### Phase 0: Agent Skill (Planning)
If this phase proceeds, feedback on the agent skill output is welcome.

### Phase 1: Python Script (Implementation)
If Phase 1 is approved:
1. Fork the repo
2. Create a feature branch
3. Implement parser, generator, or tests
4. Add test coverage
5. Submit a pull request

### Phase 2+: Gradle Integration
Gradle integration and publishing feedback welcome once Phase 1 is stable.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/<you>/jni-binding-generator.git
cd jni-binding-generator

# Install Python 3.9+
python3 --version

# Run tests (once implemented)
python3 -m pytest scripts/tests/
```

## Code Style

- **Python:** PEP 8 (use `black` for formatting)
- **Kotlin:** ktlint (for Gradle plugin, if implemented)
- **Comments:** Explain *why*, not *what*

## Reporting Issues

When this project has issues enabled:
1. Check existing issues first
2. Include: what you tried, what failed, expected behavior
3. Attach sample Kotlin code if possible

## Discussions

Ideas, questions, or feedback? Start a discussion or open an issue.

---

**Note:** This project is awaiting a go/no-go decision. See the plan for details.
