from __future__ import annotations

import unittest

from ps_sezhao.history_state import HistoryStack


class HistoryV054Tests(unittest.TestCase):
    def test_undo_and_redo_restore_snapshots(self) -> None:
        history = HistoryStack(limit=4)
        history.reset({"value": 0})
        history.record({"value": 1})
        history.record({"value": 2})

        self.assertTrue(history.can_undo)
        self.assertEqual(history.undo(), {"value": 1})
        self.assertEqual(history.undo(), {"value": 0})
        self.assertFalse(history.can_undo)
        self.assertTrue(history.can_redo)
        self.assertEqual(history.redo(), {"value": 1})
        self.assertEqual(history.redo(), {"value": 2})
        self.assertFalse(history.can_redo)

    def test_new_edit_clears_redo(self) -> None:
        history = HistoryStack()
        history.reset({"value": 0})
        history.record({"value": 1})
        history.undo()
        history.record({"value": 3})
        self.assertFalse(history.can_redo)
        self.assertEqual(history.undo(), {"value": 0})

    def test_continuous_edit_can_replace_latest_snapshot(self) -> None:
        history = HistoryStack()
        history.reset({"value": 0})
        history.record({"value": 1})
        history.record({"value": 2}, replace_last=True)
        self.assertEqual(history.undo(), {"value": 0})

    def test_history_limit_keeps_recent_states(self) -> None:
        history = HistoryStack(limit=3)
        history.reset({"value": 0})
        for value in range(1, 6):
            history.record({"value": value})
        self.assertEqual(len(history.undo_items), 3)
        self.assertEqual(history.undo_items[0], {"value": 3})


if __name__ == "__main__":
    unittest.main()
