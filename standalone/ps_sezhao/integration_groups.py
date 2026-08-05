from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import Any, Type


LEGACY_COMPATIBILITY_COMPONENTS = (
    "apply_v050_patch",
    "apply_raw_patch",
    "apply_source_crop_patch",
    "apply_scroll_patch",
    "apply_v054_patch",
    "apply_v054_sync_patch",
    "apply_v055_import_drop_patch",
    "apply_v057_rotate_output_patch",
    "apply_v060_style_library_patch",
    "apply_v061_resizable_layout_patch",
    "apply_v071_text_layout_patch",
    "apply_v072_workspace_lut_layout_patch",
    "apply_v072_responsive_group_patch",
)


@dataclass(frozen=True)
class IntegrationContext:
    app_module: ModuleType
    source_crop_module: ModuleType
    engine_module: ModuleType
    app_class: Type[Any]


def build_context() -> IntegrationContext:
    from . import app as app_module
    from . import app_v052_source_crop_patch as source_crop_module
    from . import engine as engine_module

    return IntegrationContext(
        app_module=app_module,
        source_crop_module=source_crop_module,
        engine_module=engine_module,
        app_class=app_module.SezhaoApp,
    )


def install_engine_group(context: IntegrationContext) -> None:
    from .engine_lut_v072_patch import apply_user_lut_engine_patch
    from .engine_style_v060_patch import apply_style_engine_patch
    from .engine_v053_patch import apply_engine_patch

    apply_engine_patch()
    apply_style_engine_patch()
    apply_user_lut_engine_patch()


def install_runtime_binding_group(context: IntegrationContext) -> None:
    from .services.runtime_service import install_runtime_bindings

    install_runtime_bindings(
        app_module=context.app_module,
        source_crop_module=context.source_crop_module,
        engine_module=context.engine_module,
    )


def install_legacy_ui_group(context: IntegrationContext) -> None:
    """Install the frozen pre-v0.7 UI compatibility layer in one ordered group."""

    from .app_v050_patch import apply_patch
    from .app_v051_raw_patch import apply_raw_patch
    from .app_v052_source_crop_patch import apply_source_crop_patch
    from .app_v053_scroll_patch import apply_scroll_patch
    from .app_v054_history_direct_patch import apply_v054_patch
    from .app_v054_sync_patch import apply_v054_sync_patch
    from .app_v055_import_drop_patch import apply_v055_import_drop_patch
    from .app_v057_rotate_output_patch import apply_v057_rotate_output_patch
    from .app_v060_style_library_patch import apply_v060_style_library_patch
    from .app_v061_resizable_layout_patch import apply_v061_resizable_layout_patch
    from .app_v071_text_layout_patch import apply_v071_text_layout_patch
    from .app_v072_responsive_group_patch import apply_v072_responsive_group_patch
    from .app_v072_workspace_lut_layout_patch import apply_v072_workspace_lut_layout_patch

    app_class = context.app_class
    apply_patch(app_class)
    apply_raw_patch(app_class)
    apply_source_crop_patch(app_class)
    apply_scroll_patch(app_class)
    apply_v054_patch(app_class)
    apply_v054_sync_patch(app_class)
    apply_v055_import_drop_patch(app_class)
    apply_v057_rotate_output_patch(app_class)
    apply_v060_style_library_patch(app_class)
    apply_v061_resizable_layout_patch(app_class)
    apply_v071_text_layout_patch(app_class)
    apply_v072_workspace_lut_layout_patch(app_class)
    apply_v072_responsive_group_patch(app_class)


def install_processing_service_group(context: IntegrationContext) -> None:
    """Install preview, geometry, output and multi-image services."""

    from .services.complete_output_pipeline import apply_complete_output_pipeline
    from .services.geometry_history import apply_geometry_history_guard
    from .services.geometry_pipeline import apply_geometry_pipeline
    from .services.lightroom_job_pipeline import apply_lightroom_job_pipeline
    from .services.output_defaults import apply_safe_output_defaults
    from .services.output_pipeline import apply_output_pipeline
    from .services.output_queue_compat import apply_output_queue_compatibility
    from .services.output_sync_extension import apply_output_sync_extension
    from .services.proxy_pipeline import apply_proxy_pipeline
    from .services.sync_pipeline import apply_sync_pipeline
    from .services.sync_transaction import apply_sync_transaction_guard

    app_class = context.app_class
    apply_proxy_pipeline(app_class)
    apply_geometry_pipeline(app_class)
    apply_geometry_history_guard(app_class)
    apply_output_pipeline(app_class)
    apply_complete_output_pipeline(app_class)
    apply_output_queue_compatibility()
    apply_sync_pipeline(app_class)
    apply_output_sync_extension(app_class)
    apply_safe_output_defaults(app_class)
    apply_sync_transaction_guard(app_class)
    apply_lightroom_job_pipeline(app_class)


def install_persistence_service_group(context: IntegrationContext) -> None:
    """Install workspace, roll-project and archive persistence in one group."""

    from .services.project_archive_pipeline import apply_project_archive_pipeline
    from .services.project_archive_platform_guard import apply_project_archive_platform_guard
    from .services.project_session import apply_project_session
    from .services.roll_project_pipeline import apply_roll_project_pipeline
    from .services.roll_project_state import apply_roll_project_state_guard

    app_class = context.app_class
    apply_project_session(app_class)
    apply_roll_project_pipeline(app_class)
    apply_roll_project_state_guard(app_class)
    apply_project_archive_pipeline(app_class)
    apply_project_archive_platform_guard(app_class)


def install_drag_drop_group(context: IntegrationContext) -> None:
    from .app_v055_import_drop_patch import install_drag_drop_root

    install_drag_drop_root(context.app_module)
