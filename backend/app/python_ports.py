from __future__ import annotations

import ast
import re
from dataclasses import dataclass


DEFAULT_INPUTS = ["in"]
DEFAULT_OUTPUTS = ["out"]
_PORT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class PythonPortDefinitionError(ValueError):
    """A Python Block PORTS declaration is invalid."""


@dataclass(frozen=True)
class PythonPorts:
    inputs: list[str]
    outputs: list[str]
    explicit: bool = False


def _names(value: object, direction: str) -> list[str]:
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
        raise PythonPortDefinitionError(f"PORTS['{direction}'] must be a list of port names")
    names = list(value)
    if len(names) != len(set(names)):
        raise PythonPortDefinitionError(f"PORTS['{direction}'] contains duplicate names")
    for name in names:
        if not _PORT_NAME.fullmatch(name) or name == "__metrics__":
            raise PythonPortDefinitionError(f"PORTS['{direction}'] has invalid port name '{name}'")
    return names


def parse_python_ports(code: str | None) -> PythonPorts:
    source = str(code or "")
    try:
        tree = ast.parse(source, filename="<python-block>", mode="exec")
    except SyntaxError as exc:
        raise PythonPortDefinitionError(f"Line {exc.lineno or '?'}: {exc.msg or 'invalid Python syntax'}") from exc
    declaration: ast.AST | None = None
    for statement in tree.body:
        target = None
        value = None
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            target, value = statement.targets[0].id, statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            target, value = statement.target.id, statement.value
        if target == "PORTS":
            if declaration is not None:
                raise PythonPortDefinitionError("PORTS may only be declared once")
            declaration = value
    if declaration is None:
        return PythonPorts(DEFAULT_INPUTS.copy(), DEFAULT_OUTPUTS.copy(), False)
    try:
        raw = ast.literal_eval(declaration)
    except (TypeError, ValueError) as exc:
        raise PythonPortDefinitionError("PORTS must be a literal dictionary") from exc
    if not isinstance(raw, dict):
        raise PythonPortDefinitionError("PORTS must be a dictionary with 'inputs' and 'outputs'")
    unknown = set(raw) - {"inputs", "outputs"}
    if unknown:
        raise PythonPortDefinitionError(f"PORTS has unknown key(s): {', '.join(sorted(map(str, unknown)))}")
    return PythonPorts(_names(raw.get("inputs", DEFAULT_INPUTS), "inputs"), _names(raw.get("outputs", DEFAULT_OUTPUTS), "outputs"), True)
