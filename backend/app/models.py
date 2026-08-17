from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Position(BaseModel):
    x: float = 0
    y: float = 0


class Node(BaseModel):
    id: str
    type: str
    label: str = "Block"
    position: Position = Field(default_factory=Position)
    params: dict[str, Any] = Field(default_factory=dict)
    code: str | None = None
    port_orientation: Literal["standard", "reversed"] = "standard"


class Edge(BaseModel):
    id: str
    source: str
    target: str
    source_handle: str = "out"
    target_handle: str = "in"


class Graph(BaseModel):
    version: str = "1.0"
    nodes: list[Node]
    edges: list[Edge]

    @field_validator("nodes")
    @classmethod
    def unique_nodes(cls, nodes: list[Node]) -> list[Node]:
        ids = [node.id for node in nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("Node ids must be unique")
        return nodes


class SimulationConfig(BaseModel):
    trials: int = Field(default=100, ge=1, le=1_000_000)
    workers: int = Field(default=0, ge=0, le=256)
    seed: int = Field(default=2026, ge=0, le=2**32 - 1)
    device: Literal["auto", "cpu", "gpu"] = "auto"
    chunk_size: int = Field(default=10, ge=1, le=100_000)


class SimulationRequest(BaseModel):
    graph: Graph
    config: SimulationConfig = Field(default_factory=SimulationConfig)


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
