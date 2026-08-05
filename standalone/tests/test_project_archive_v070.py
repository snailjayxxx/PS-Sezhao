from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from ps_sezhao.core.output import OutputSettings
from ps_sezhao.core.roll_project import RollProjectSettings
from ps_sezhao.storage.project_archive import (
    ARCHIVE_SUFFIX,
    backup_project_database,
    check_project_integrity,
    export_project_archive,
    import_project_archive,
    inspect_project_archive,
    relink_project_sources,
    restore_project_database,
)
from ps_sezhao.storage.roll_project_store import RollProjectStore


class ProjectArchiveTests(unittest.TestCase):
    def _build_project(self, root: Path, store: RollProjectStore) -> tuple[str, list[Path]]:
        root.mkdir(parents=True, exist_ok=True)
        sources: list[Path] = []
        for index in range(2):
            path = root / f"frame-{index + 1}.png"
            Image.new("RGB", (64, 48), (120 + index * 20, 80, 40)).save(path)
            sources.append(path)
        project_id = store.create_project(
            "Tokyo Roll",
            shared=RollProjectSettings(
                roll_name="Tokyo-2026",
                film_stock="Portra 400",
                camera="Flextight X5",
                frame_prefix="T-",
                frame_start=1,
                frame_padding=3,
            ).to_dict(),
        )
        preset_id = store.save_output_preset(
            "Web JPEG",
            OutputSettings(
                format_label="JPEG",
                color_space="srgb",
                resize_mode="long_edge",
                resize_value=2400,
            ).to_dict(),
        )
        store.save_project(
            project_id=project_id,
            name="Tokyo Roll",
            shared=RollProjectSettings(
                roll_name="Tokyo-2026",
                film_stock="Portra 400",
                camera="Flextight X5",
                frame_prefix="T-",
                frame_start=1,
                frame_padding=3,
            ).to_dict(),
            image_states=[
                {
                    "file_path": sources[0],
                    "controls": {"exposure": 0.4},
                    "crop": (0.0, 0.0, 1.0, 1.0),
                    "output_settings": {"frame_number": "T-001"},
                },
                {
                    "file_path": sources[1],
                    "controls": {"exposure": -0.2},
                    "crop": (0.1, 0.1, 0.9, 0.9),
                    "output_settings": {"frame_number": "T-002"},
                },
            ],
            file_paths=sources,
            current_file=sources[1],
            output_preset_id=preset_id,
        )
        return project_id, sources

    def test_archive_with_originals_round_trips_to_another_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_store = RollProjectStore(root / "source.sqlite3")
            project_id, _sources = self._build_project(root / "sources", source_store)
            archive = root / "Tokyo Roll"
            result = export_project_archive(
                source_store,
                project_id,
                archive,
                include_originals=True,
            )
            self.assertEqual(result.path.suffix, ARCHIVE_SUFFIX)
            self.assertEqual(result.item_count, 2)
            self.assertEqual(result.bundled_original_count, 2)
            self.assertEqual(result.missing_original_count, 0)
            self.assertEqual(len(result.sha256), 64)

            inspection = inspect_project_archive(result.path)
            self.assertEqual(inspection.project_name, "Tokyo Roll")
            self.assertEqual(inspection.item_count, 2)
            self.assertTrue(inspection.contains_originals)

            target_store = RollProjectStore(root / "target.sqlite3")
            imported = import_project_archive(
                target_store,
                result.path,
                extract_originals_to=root / "restored-originals",
            )
            self.assertEqual(imported.item_count, 2)
            self.assertEqual(imported.extracted_original_count, 2)
            self.assertEqual(imported.missing_original_count, 0)
            project = target_store.load_project(imported.project_id)
            self.assertIsNotNone(project)
            self.assertEqual(project.shared["film_stock"], "Portra 400")
            self.assertEqual(project.items[0].frame_number, "T-001")
            self.assertEqual(project.items[1].frame_number, "T-002")
            self.assertAlmostEqual(project.items[0].state["controls"]["exposure"], 0.4)
            self.assertTrue(all(Path(item.file_path).is_file() for item in project.items))
            self.assertIsNotNone(project.output_preset_id)
            self.assertEqual(target_store.load_output_preset(project.output_preset_id).name, "Web JPEG")
            report = check_project_integrity(target_store, imported.project_id, verify_hashes=True)
            self.assertTrue(report.ok)
            self.assertEqual(report.available, 2)

    def test_external_archive_can_relink_after_original_folder_moves(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original_root = root / "original"
            original_root.mkdir()
            store = RollProjectStore(root / "workspace.sqlite3")
            project_id, sources = self._build_project(original_root, store)
            archive = export_project_archive(
                store,
                project_id,
                root / "external.psszproj",
                include_originals=False,
            )
            moved_root = root / "moved"
            moved_root.mkdir()
            moved_sources = []
            for source in sources:
                destination = moved_root / source.name
                source.replace(destination)
                moved_sources.append(destination)

            imported_store = RollProjectStore(root / "imported.sqlite3")
            imported = import_project_archive(imported_store, archive.path)
            before = check_project_integrity(imported_store, imported.project_id)
            self.assertEqual(len(before.missing_paths), 2)

            relinked = relink_project_sources(
                imported_store,
                imported.project_id,
                [moved_root],
            )
            self.assertEqual(relinked.relinked_count, 2)
            self.assertEqual(relinked.unresolved_count, 0)
            self.assertEqual(relinked.ambiguous_count, 0)
            project = imported_store.load_project(imported.project_id)
            self.assertEqual(
                {Path(item.file_path).name for item in project.items},
                {path.name for path in moved_sources},
            )
            after = check_project_integrity(imported_store, imported.project_id, verify_hashes=True)
            self.assertTrue(after.ok)

    def test_integrity_reports_changed_files_and_duplicate_frames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = RollProjectStore(root / "workspace.sqlite3")
            project_id, sources = self._build_project(root / "sources", store)
            archive = export_project_archive(store, project_id, root / "portable", include_originals=False)
            imported_store = RollProjectStore(root / "imported.sqlite3")
            imported = import_project_archive(imported_store, archive.path)
            project = imported_store.load_project(imported.project_id)
            states = [dict(item.state) for item in project.items]
            states[1]["output_settings"] = {
                **dict(states[1].get("output_settings") or {}),
                "frame_number": "T-001",
            }
            imported_store.save_project(
                project_id=project.project_id,
                name=project.name,
                shared=project.shared,
                image_states=states,
                file_paths=[item.file_path for item in project.items],
                current_file=project.current_file,
                output_preset_id=project.output_preset_id,
            )
            Image.new("RGB", (80, 60), (1, 2, 3)).save(sources[0])
            report = check_project_integrity(imported_store, imported.project_id, verify_hashes=True)
            self.assertGreaterEqual(len(report.changed_paths) + len(report.hash_mismatches), 1)
            self.assertEqual(len(report.duplicate_frame_numbers), 2)
            self.assertFalse(report.ok)

    def test_database_backup_and_restore_preserve_projects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = RollProjectStore(root / "workspace.sqlite3")
            project_id, _sources = self._build_project(root / "sources", store)
            backup = backup_project_database(store, root / "backup.sqlite3")
            self.assertTrue(backup.is_file())
            store.delete_project(project_id)
            self.assertIsNone(store.load_project(project_id))
            restore_project_database(store, backup)
            restored = store.load_project(project_id)
            self.assertIsNotNone(restored)
            self.assertEqual(restored.name, "Tokyo Roll")
            self.assertEqual(len(restored.items), 2)


if __name__ == "__main__":
    unittest.main()
