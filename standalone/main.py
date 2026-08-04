from ps_sezhao import app as app_module
from ps_sezhao.processing import process_image_tiled

# Use the same bounded-memory renderer for preview, single-image save and batch output.
# Small previews remain responsive; large scans avoid full-frame temporary arrays.
app_module.process_image = process_image_tiled

if __name__ == "__main__":
    raise SystemExit(app_module.main())
