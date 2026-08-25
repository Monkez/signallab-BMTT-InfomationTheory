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
    mode: Literal["specific_steps", "ber_benchmark"] = "specific_steps"
    trials: int = Field(default=100, ge=1, le=1_000_000)
    max_frames: int | None = Field(default=1, ge=1, le=1_000_000)
    min_frames: int = Field(default=1, ge=1, le=1_000_000)
    min_errors: int = Field(default=0, ge=0, le=1_000_000)
    snr_db_start: float = -2.0
    snr_db_stop: float = 10.0
    snr_db_step: float = Field(default=2.0, gt=0)
    snr_db_points: list[float] = Field(default_factory=lambda: [0.0], min_length=1, max_length=10_000)
    workers: int = Field(default=0, ge=0, le=256)
    seed: int = Field(default=2026, ge=0, le=2**32 - 1)
    device: Literal["auto", "cpu", "gpu"] = "auto"
    engine: Literal["auto", "native", "python"] = "auto"
    chunk_size: int = Field(default=10, ge=1, le=100_000)


class SimulationRequest(BaseModel):
    graph: Graph
    config: SimulationConfig = Field(default_factory=SimulationConfig)


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    node_errors: dict[str, list[str]] = Field(default_factory=dict)
