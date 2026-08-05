from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HistoryStack:
    """Small per-photo undo/redo stack with snapshot de-duplication."""

    limit: int = 60
    undo_items: list[dict[str, Any]] = field(default_factory=list)
    redo_items: list[dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def _copy(snapshot: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(snapshot)

    def reset(self, snapshot: dict[str, Any]) -> None:
        self.undo_items = [self._copy(snapshot)]
        self.redo_items.clear()

    def record(self, snapshot: dict[str, Any], *, replace_last: bool = False) -> bool:
        current = self._copy(snapshot)
        if not self.undo_items:
            self.undo_items.append(current)
            self.redo_items.clear()
            return True
        if self.undo_items[-1] == current:
            return False
        if replace_last and len(self.undo_items) > 1:
            self.undo_items[-1] = current
        else:
            self.undo_items.append(current)
            if len(self.undo_items) > self.limit:
                self.undo_items = self.undo_items[-self.limit :]
        self.redo_items.clear()
        return True

    @property
    def can_undo(self) -> bool:
        return len(self.undo_items) > 1

    @property
    def can_redo(self) -> bool:
        return bool(self.redo_items)

    def undo(self) -> dict[str, Any] | None:
        if not self.can_undo:
            return None
        self.redo_items.append(self.undo_items.pop())
        return self._copy(self.undo_items[-1])

    def redo(self) -> dict[str, Any] | None:
        if not self.redo_items:
            return None
        snapshot = self.redo_items.pop()
        self.undo_items.append(self._copy(snapshot))
        return self._copy(snapshot)
