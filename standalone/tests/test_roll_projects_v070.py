from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from ps_sezhao.bootstrap import integration_steps
from ps_sezhao.core.output import OutputSettings
from ps_sezhao.core.roll_project import (
    RollProjectSettings,
    assign_project_output_settings,
    calculate_project_progress,
)
from ps_sezhao.storage.roll_project_store import RollProjectStore
from ps_sezhao.ui import create_application, create_root
from ps_sezhao.workspace import PhotoState


class RollProjectCoreTests(unittest.TestCase):
    def test_frame_numbers_and_project_defaults_are_deterministic(self) -> None:
        settings = RollProjectSettings(
            roll_name="Tokyo-01",
            film_stock="Portra 400",
            camera="Flextight X5",
            frame_prefix="A-",
            frame_start=7,
            frame_padding=3,
        )
        items = [
            PhotoState(Path("one.tif"), output_settings={}),
            PhotoState(Path("two.tif"), output_settings={"frame_number": "KEEP"}),
            PhotoState(Path("three.tif"), output_settings={}),
        ]
        assigned = assign_project_output_settings(items, settings, renumber_all=False)
        self.assertEqual(assigned, ("A-007", "KEEP", "A-009"))
        self.assertEqual(items[0].output_settings["roll_name"], "Tokyo-01")
        self.assertEqual(items[0].output_settings["film_stock"], "Portra 400")
        self.assertEqual(items[0].output_settings["camera"], "Flextight X5")

        renumbered = assign_project_output_settings(items, settings, renumber_all=True)
        self.assertEqual(renumbered, ("A-007", "A-008", "A-009"))

    def test_progress_counts_analysis_edit_and_export_status(self) -> None:
        first = PhotoState(Path("one.tif"), analysis={"base": [1, 1, 1]})
        second = PhotoState(Path("two.tif"), crop=(0.1, 0.1, 0.9, 0.9))
        third = PhotoState(Path("three.tif"))
        progress = calculate_project_progress([first, second, third], [second.path])
        self.assertEqual(progress.total, 3)
        self.assertEqual(progress.analyzed, 1)
        self.assertEqual(progress.edited, 2)
        self.assertEqual(progress.exported, 1)
        self.assertEqual(progress.pending, 2)
        self.assertEqual(progress.percent, 33)


class RollProjectStoreTests(unittest.TestCase):
    def test_multiple_projects_presets_and_export_state_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "workspace.sqlite3"
            store = RollProjectStore(database)
            first_id = store.create_project(
                "Roll One",
                shared=RollProjectSettings(roll_name="R1", frame_prefix="R-").to_dict(),
            )
            second_id = store.create_project("Roll Two", make_active=False)
            preset_id = store.save_output_preset(
                "Web JPEG",
                OutputSettings(
                    format_label="JPEG",
                    color_space="srgb",
                    resize_mode="long_edge",
                    resize_value=2400,
                ).to_dict(),
            )
            one = Path(directory) / "one.tif"
            two = Path(directory) / "two.tif"
            store.save_project(
                project_id=first_id,
                name="Roll One",
                shared=RollProjectSettings(roll_name="R1", frame_prefix="R-").to_dict(),
                image_states=[
                    {"file_path": one, "output_settings": {"frame_number": "R-0001"}},
                    {"file_path": two, "output_settings": {"frame_number": "R-0002"}},
                ],
                file_paths=[one, two],
                current_file=two,
                output_preset_id=preset_id,
            )
            store.mark_exported(first_id, one, Path(directory) / "out-one.jpg", exported_at=123)

            loaded = store.load_project(first_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.name, "Roll One")
            self.assertEqual(loaded.current_file, str(two.resolve(strict=False)))
            self.assertEqual(loaded.output_preset_id, preset_id)
            self.assertEqual(len(loaded.items), 2)
            self.assertEqual(loaded.items[0].frame_number, "R-0001")
            self.assertEqual(loaded.items[0].exported_at, 123)
            self.assertTrue(loaded.items[0].last_output.endswith("out-one.jpg"))

            projects = store.list_projects()
            self.assertEqual({project.project_id for project in projects}, {first_id, second_id})
            first_summary = next(project for project in projects if project.project_id == first_id)
            self.assertEqual(first_summary.item_count, 2)
            self.assertEqual(first_summary.exported_count, 1)
            self.assertEqual(store.get_active_project_id(), first_id)

            preset = store.load_output_preset(preset_id)
            self.assertIsNotNone(preset)
            self.assertEqual(preset.name, "Web JPEG")
            self.assertEqual(preset.settings["format_label"], "JPEG")
            self.assertEqual(len(store.list_output_presets()), 1)


class RollProjectSessionTests(unittest.TestCase):
    def test_active_roll_project_restores_across_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root_path = Path(directory)
            database = root_path / "workspace.sqlite3"
            image_paths = []
            for index in range(2):
                path = root_path / f"negative-{index}.png"
                image = Image.new("RGB", (96, 72), (230, 145, 75))
                ImageDraw.Draw(image).rectangle((12, 10, 84, 62), fill=(80 + index * 5, 55, 40))
                image.save(path)
                image_paths.append(path)

            with patch.dict(os.environ, {"PS_SEZHAO_PROJECT_DB": str(database)}):
                first_root = create_root()
                first_root.withdraw()
                try:
                    first_app = create_application(
                        first_root,
                        initial_files=[str(path) for path in image_paths],
                    )
                    first_root.update_idletasks()
                    project_id = first_app.roll_project_store.create_project(
                        "Family Roll",
                        shared=RollProjectSettings(
                            roll_name="Family-2026",
                            film_stock="Gold 200",
                            frame_prefix="F-",
                            frame_start=1,
                            frame_padding=3,
                        ).to_dict(),
                    )
                    first_app.active_roll_project_id = project_id
                    first_app.active_roll_project_name = "Family Roll"
                    first_app.active_roll_project_settings = RollProjectSettings(
                        roll_name="Family-2026",
                        film_stock="Gold 200",
                        frame_prefix="F-",
                        frame_start=1,
                        frame_padding=3,
                    )
                    assign_project_output_settings(
                        first_app.items,
                        first_app.active_roll_project_settings,
                        renumber_all=True,
                    )
                    first_app.vars["exposure"].set(0.65)
                    first_app._store_current_state()
                    first_app._save_project_session_now()
                    stored = first_app.roll_project_store.load_project(project_id)
                    self.assertIsNotNone(stored)
                    self.assertEqual(stored.items[0].frame_number, "F-001")
                    self.assertEqual(stored.items[1].frame_number, "F-002")
                finally:
                    first_root.destroy()

                second_root = create_root()
                second_root.withdraw()
                try:
                    second_app = create_application(second_root)
                    second_root.update_idletasks()
                    self.assertEqual(second_app.active_roll_project_id, project_id)
                    self.assertEqual(second_app.active_roll_project_name, "Family Roll")
                    self.assertEqual(len(second_app.items), 2)
                    self.assertEqual(second_app.items[0].output_settings["frame_number"], "F-001")
                    self.assertEqual(second_app.items[1].output_settings["frame_number"], "F-002")
                    self.assertEqual(second_app.items[0].output_settings["film_stock"], "Gold 200")
                    self.assertAlmostEqual(second_app.vars["exposure"].get(), 0.65)
                    self.assertIn("Family Roll", second_app.active_roll_title.get())
                finally:
                    second_root.destroy()

    def test_bootstrap_wires_roll_projects_after_workspace_storage(self) -> None:
        names = tuple(step.name for step in integration_steps())
        self.assertLess(names.index("storage.project_session"), names.index("storage.roll_projects"))
        self.assertLess(names.index("storage.roll_projects"), names.index("storage.roll_project_state"))
        self.assertLess(names.index("storage.roll_project_state"), names.index("runtime.drag_drop_root"))


if __name__ == "__main__":
    unittest.main()
