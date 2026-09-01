from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Generic, TypeVar

from fakebric.powerbi.common import VersionedResource, utc_now

T = TypeVar("T", bound=VersionedResource)


class RepositoryError(Exception):
    pass


class NotFoundError(RepositoryError):
    pass


class ConflictError(RepositoryError):
    pass


@dataclass(frozen=True)
class StoredResource(Generic[T]):
    resource: T
    etag: str


class InMemoryRevisionRepository(Generic[T]):
    """Day-1 revision repository contract with optimistic concurrency."""

    def __init__(self) -> None:
        self._history: dict[str, list[T]] = {}

    def create(self, resource: T) -> StoredResource[T]:
        if resource.id in self._history:
            raise ConflictError(resource.id)
        item = resource.model_copy(deep=True)
        self._history[item.id] = [item]
        return StoredResource(deepcopy(item), item.etag())

    def get(self, resource_id: str) -> StoredResource[T]:
        try:
            item = self._history[resource_id][-1]
        except KeyError as exc:
            raise NotFoundError(resource_id) from exc
        return StoredResource(deepcopy(item), item.etag())

    def update(self, resource_id: str, replacement: T, if_match: str) -> StoredResource[T]:
        current = self.get(resource_id)
        if current.etag != if_match:
            raise ConflictError("ETag mismatch")
        if replacement.id != resource_id:
            raise ConflictError("resource id is immutable")
        next_item = replacement.model_copy(
            update={"revision": current.resource.revision + 1, "updated_at": utc_now()},
            deep=True,
        )
        self._history[resource_id].append(next_item)
        return StoredResource(deepcopy(next_item), next_item.etag())

    def revisions(self, resource_id: str) -> tuple[T, ...]:
        if resource_id not in self._history:
            raise NotFoundError(resource_id)
        return tuple(deepcopy(self._history[resource_id]))
