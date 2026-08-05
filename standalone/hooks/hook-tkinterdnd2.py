from PyInstaller.utils.hooks import collect_data_files

# TkinterDnD2 ships platform-specific TkDnD shared libraries and Tcl scripts
# as package data. PyInstaller needs this hook so the frozen app can load the
# native drag-and-drop extension at runtime.
datas = collect_data_files("tkinterdnd2")
