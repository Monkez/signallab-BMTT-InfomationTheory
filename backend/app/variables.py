from __future__ import annotations

import ast
import math
from typing import Any, Iterable


RUNTIME_PARAM_NAMES = {"snr_db", "trial_index", "frame_seed", "device", "experiment", "variables"}


class VariableDefinitionError(ValueError):
    """A Variables block contains unsafe or invalid declarations."""


def _validate_value(value: Any, path: str) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise VariableDefinitionError(f"{path} must be finite")
        return value
    if isinstance(value, (list, tuple)):
        return type(value)(_validate_value(item, f"{path}[{index}]") for index, item in enumerate(value))
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise VariableDefinitionError(f"{path} dictionary keys must be strings")
        return {key: _validate_value(item, f"{path}.{key}") for key, item in value.items()}
    raise VariableDefinitionError(f"{path} uses unsupported type {type(value).__name__}")


def parse_variable_definitions(definitions: Any) -> dict[str, Any]:
    source = str(definitions or "").strip()
    if not source:
        return {}
    try:
        tree = ast.parse(source, filename="<variables-block>", mode="exec")
    except SyntaxError as exc:
        raise VariableDefinitionError(f"Line {exc.lineno or '?'}: {exc.msg or 'invalid syntax'}") from exc

    variables: dict[str, Any] = {}
    for statement in tree.body:
        line = getattr(statement, "lineno", "?")
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            raise VariableDefinitionError(f"Line {line}: use one assignment such as name = value")
        name = statement.targets[0].id
        if name in RUNTIME_PARAM_NAMES:
            raise VariableDefinitionError(f"Line {line}: '{name}' is reserved by the runtime")
        if name.startswith("_"):
            raise VariableDefinitionError(f"Line {line}: variable names must not start with '_'")
        if name in variables:
            raise VariableDefinitionError(f"Line {line}: duplicate variable '{name}'")
        try:
            value = ast.literal_eval(statement.value)
        except (TypeError, ValueError) as exc:
            raise VariableDefinitionError(f"Line {line}: '{name}' must use a literal value") from exc
        variables[name] = _validate_value(value, name)
    return variables


def collect_global_variables(nodes: Iterable[Any]) -> dict[str, Any]:
    blocks = [node for node in nodes if (node.get("type") if isinstance(node, dict) else node.type) == "variables"]
    if not blocks:
        return {}
    if len(blocks) > 1:
        raise VariableDefinitionError("Only one Variables block is allowed in a simulation")
    block = blocks[0]
    params = block.get("params", {}) if isinstance(block, dict) else block.params
    return parse_variable_definitions(params.get("definitions", ""))
