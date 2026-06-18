# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)


datas = [
    ("dashboard.py", "."),
    ("data/polskie_miejscowosci.json", "data"),
]

datas += collect_data_files("streamlit")
datas += copy_metadata("streamlit")

hiddenimports = [
    "dashboard",
    "db",
    "etl_customers",
    "etl_inventory",
    "etl_products",
    "models",
    "repositories",
    "services",
]

hiddenimports += collect_submodules("streamlit")


a = Analysis(
    ["app_launcher.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="etl-dashboard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="etl-dashboard",
)
