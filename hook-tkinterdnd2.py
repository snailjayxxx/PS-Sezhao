from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect the Tcl scripts and platform-specific TkDND binaries shipped by the
# installed tkinterdnd2 package. The explicit hook keeps one-file and app-bundle
# builds aligned with the package's supported PyInstaller setup.
datas = collect_data_files("tkinterdnd2")
hiddenimports = collect_submodules("tkinterdnd2")
