from __future__ import annotations

from dataclasses import dataclass, field

# Exit codes
EXIT_OK = 0
EXIT_USAGE = 1  # no files / nothing to generate / bad path
EXIT_PARSE = 2  # unrecognized type or parse failure
EXIT_DRIFT = 3  # --check found out-of-date / missing output


@dataclass
class Param:
    name: str
    kotlin_type: str


@dataclass
class ExternalFunction:
    name: str
    params: list[Param]
    return_type: str | None
    line: int = 0  # 1-based line of the declaration in the source file


@dataclass
class ParsedFile:
    package: str
    class_name: str
    is_static: bool  # object / companion -> static (jclass)
    functions: list[ExternalFunction] = field(default_factory=list)
