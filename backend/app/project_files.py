from __future__ import annotations

import os
import tempfile
from pathlib import Path


PROJECT_SUFFIX = ".slab.json"


def ensure_project_suffix(path: Path) -> Path:
    name = path.name
    if name.lower().endswith(".json"):
        return path
    return path.with_name(f"{name}{PROJECT_SUFFIX}")


def read_project_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_project_text(path: Path, content: str) -> Path:
    target = ensure_project_suffix(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, target)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return target
