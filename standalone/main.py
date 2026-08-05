from ps_sezhao import app as app_module
from ps_sezhao.app_v050_patch import apply_patch
from ps_sezhao.app_v051_raw_patch import apply_raw_patch
from ps_sezhao.app_v052_source_crop_patch import apply_source_crop_patch
from ps_sezhao.app_v053_scroll_patch import apply_scroll_patch
from ps_sezhao.engine_v053_patch import apply_engine_patch
from ps_sezhao.processing import process_image_tiled

# Use the same bounded-memory renderer for preview, single-image save and batch output.
# Small previews remain responsive; large scans avoid full-frame temporary arrays.
apply_engine_patch()
app_module.process_image = process_image_tiled
apply_patch(app_module.SezhaoApp)
apply_raw_patch(app_module.SezhaoApp)
apply_source_crop_patch(app_module.SezhaoApp)
apply_scroll_patch(app_module.SezhaoApp)

if __name__ == "__main__":
    raise SystemExit(app_module.main())
