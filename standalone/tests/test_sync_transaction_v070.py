from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

from ps_sezhao.services.sync_transaction import apply_sync_transaction_guard
from ps_sezhao.workspace import PhotoState


class _Variable:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value


class _Status:
    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        self.value = value


class _Dialog:
    def __init__(self) -> None:
        self.destroyed = False

    def destroy(self) -> None:
        self.destroyed = True


class SyncTransactionTests(unittest.TestCase):
    def make_application(self, *, fail_index: int | None = None):
        class FakeApplication:
            def _store_current_state(self) -> None:
                return None

            def current_item(self) -> PhotoState:
                return self.items[0]

            def _history_for(self, index: int) -> None:
                return None

            def _update_tree_row(self, index: int) -> None:
                if self.fail_index == index:
                    raise RuntimeError("tree update failed")

            def _record_history(self, **_kwargs) -> None:
                self.history_recorded = True

            def _save_project_session_now(self) -> None:
                self.saved = True

        apply_sync_transaction_guard(FakeApplication)
        app = FakeApplication()
        app.items = [
            PhotoState(Path("source.tif"), controls={"exposure": 1.0}),
            PhotoState(Path("target-1.tif"), controls={"exposure": -1.0}),
            PhotoState(Path("target-2.tif"), controls={"exposure": -2.0}),
        ]
        app.fail_index = fail_index
        app.history_recorded = False
        app.saved = False
        app.status = _Status()
        return app

    def test_failure_restores_every_target(self) -> None:
        app = self.make_application(fail_index=2)
        originals = tuple(app.items)
        dialog = _Dialog()
        with mock.patch("ps_sezhao.services.sync_transaction.messagebox.showerror") as show_error:
            app._apply_sync_dialog(
                dialog,
                {"tone": _Variable(True)},
                [1, 2],
            )
        self.assertIs(app.items[1], originals[1])
        self.assertIs(app.items[2], originals[2])
        self.assertFalse(app.saved)
        self.assertFalse(dialog.destroyed)
        show_error.assert_called_once()

    def test_success_commits_all_targets_once(self) -> None:
        app = self.make_application()
        dialog = _Dialog()
        app._apply_sync_dialog(
            dialog,
            {"tone": _Variable(True)},
            [1, 2],
        )
        self.assertEqual(app.items[1].controls["exposure"], 1.0)
        self.assertEqual(app.items[2].controls["exposure"], 1.0)
        self.assertTrue(app.history_recorded)
        self.assertTrue(app.saved)
        self.assertTrue(dialog.destroyed)


if __name__ == "__main__":
    unittest.main()
