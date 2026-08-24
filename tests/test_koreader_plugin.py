from __future__ import annotations

import stat
import zipfile
from pathlib import Path

import pytest

from scripts.build_koreader_plugin import PLUGIN_FOLDER, build_archive


def test_build_archive_has_expected_plugin_layout(tmp_path: Path) -> None:
    source = tmp_path / "plugin"
    locale = source / "lua" / "locale"
    locale.mkdir(parents=True)
    (source / "lua" / "main.lua").write_text("return {}\n", encoding="utf-8")
    (source / "lua" / "_meta.lua").write_text("return {}\n", encoding="utf-8")
    (locale / "README.md").write_text("translations\n", encoding="utf-8")
    (source / "LICENSE").write_text("license\n", encoding="utf-8")
    binary = tmp_path / "receiver"
    binary.write_bytes(b"receiver-binary")
    output = tmp_path / "receiver.zip"

    build_archive(source, binary, "armv7", output)

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert f"{PLUGIN_FOLDER}/main.lua" in names
        assert f"{PLUGIN_FOLDER}/_meta.lua" in names
        assert f"{PLUGIN_FOLDER}/locale/README.md" in names
        assert archive.read(f"{PLUGIN_FOLDER}/localsend") == b"receiver-binary"
        mode = archive.getinfo(f"{PLUGIN_FOLDER}/localsend").external_attr >> 16
        assert mode & stat.S_IXUSR


def test_build_archive_rejects_unknown_architecture(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported KOReader architecture"):
        build_archive(tmp_path, tmp_path / "missing", "x86_64", tmp_path / "bad.zip")
