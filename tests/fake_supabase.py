"""A fake of the postgrest fluent interface, backed by a list of dicts.

This exists so ``SupabaseFeedRepository`` can be held to the same contract tests
as the in-memory store without a database. It is a fake, not a mock: it really
stores rows and really applies the filters, so a missing ``.eq("user_id", ...)``
in the repository shows up as a cross-user leak in a test rather than in
production.

It implements only the subset of postgrest the repository actually uses. If the
repository starts using something else, this raises rather than silently
returning everything, which would turn a leak into a passing test.
"""

from __future__ import annotations

import copy
from typing import Any
from uuid import uuid4


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _Query:
    def __init__(self, table: "_Table", op: str, payload: Any = None) -> None:
        self._table = table
        self._op = op
        self._payload = payload
        self._filters: list = []
        self._limit: int | None = None
        self._order: tuple[str, bool] | None = None

    # --- filters ---

    def eq(self, column: str, value: Any) -> "_Query":
        self._filters.append(lambda row: row.get(column) == value)
        return self

    def in_(self, column: str, values: list) -> "_Query":
        self._filters.append(lambda row: row.get(column) in values)
        return self

    def is_(self, column: str, value: str) -> "_Query":
        if value != "null":
            raise NotImplementedError(f"is_ only supports null, got {value!r}")
        self._filters.append(lambda row: row.get(column) is None)
        return self

    def gte(self, column: str, value: str) -> "_Query":
        self._filters.append(
            lambda row: row.get(column) is not None and row[column] >= value
        )
        return self

    def lt(self, column: str, value: str) -> "_Query":
        self._filters.append(
            lambda row: row.get(column) is not None and row[column] < value
        )
        return self

    # --- shaping ---

    def order(self, column: str, desc: bool = False) -> "_Query":
        self._order = (column, desc)
        return self

    def limit(self, count: int) -> "_Query":
        self._limit = count
        return self

    # --- execution ---

    def execute(self) -> _Result:
        matched = [row for row in self._table.rows if self._matches(row)]

        if self._op == "select":
            if self._order is not None:
                column, desc = self._order
                matched.sort(key=lambda row: row.get(column) or "", reverse=desc)
            if self._limit is not None:
                matched = matched[: self._limit]
            return _Result(copy.deepcopy(matched))

        if self._op == "insert":
            row = {"id": str(uuid4()), "status": "unread", **self._payload}
            self._table.rows.append(row)
            return _Result([copy.deepcopy(row)])

        if self._op == "update":
            for row in matched:
                row.update(self._payload)
            return _Result(copy.deepcopy(matched))

        if self._op == "delete":
            for row in matched:
                self._table.rows.remove(row)
            return _Result(copy.deepcopy(matched))

        raise NotImplementedError(self._op)

    def _matches(self, row: dict) -> bool:
        return all(predicate(row) for predicate in self._filters)


class _Table:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def select(self, _columns: str = "*") -> _Query:
        return _Query(self, "select")

    def insert(self, payload: dict) -> _Query:
        return _Query(self, "insert", payload)

    def update(self, payload: dict) -> _Query:
        return _Query(self, "update", payload)

    def delete(self) -> _Query:
        return _Query(self, "delete")


class FakeSupabaseClient:
    def __init__(self) -> None:
        self._tables: dict[str, _Table] = {}

    def table(self, name: str) -> _Table:
        return self._tables.setdefault(name, _Table())
