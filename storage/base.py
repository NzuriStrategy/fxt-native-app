"""
storage.base — Abstract repository contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar("T")


class AbstractRepository(ABC):
    """
    Generic repository interface.

    All concrete repositories in the pipeline implement this contract,
    enabling easy substitution (e.g. swapping Postgres for SQLite in tests).
    """

    @abstractmethod
    def upsert(self, record: object) -> None:
        """
        Insert or update a single record.
        The concrete type of `record` is defined by the subclass.
        """
        ...

    @abstractmethod
    def upsert_many(self, records: list) -> None:
        """
        Bulk upsert. Should use a single transaction for atomicity.
        """
        ...
