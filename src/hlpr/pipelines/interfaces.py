"""Interfaces (Protocols) and DTOs bridging persistence and pipeline orchestration."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class DocumentDTO:
    id: int
    project_id: int
    title: str
    content: str


class DocumentRepositoryProtocol(Protocol):
    async def get(self, doc_id: int) -> DocumentDTO | None: ...  # noqa: D401,E701
    async def list_by_project(self, project_id: int, limit: int = 50) -> Sequence[DocumentDTO]: ...


class PipelineRunRepositoryProtocol(Protocol):
    async def start(self, pipeline: str, input_ref: str) -> int: ...
    async def complete(self, run_id: int, output: dict[str, Any]) -> None: ...


class RetrievalInterface(Protocol):
    async def retrieve(self, project_id: int, query: str, k: int = 5) -> Sequence[DocumentDTO]: ...
