"""Build a deterministic installable KOReader receiver archive."""

from __future__ import annotations

import argparse
import stat
import zipfile
from pathlib import Path

PLUGIN_FOLDER = "pdf_to_epub_receiver.koplugin"
SUPPORTED_ARCHITECTURES = {"arm-legacy", "armv7", "arm64"}
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def _write_file(
    archive: zipfile.ZipFile,
    source: Path,
    destination: str,
    *,
    executable: bool = False,
) -> None:
    info = zipfile.ZipInfo(destination, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    mode = stat.S_IFREG | (0o755 if executable else 0o644)
    info.external_attr = mode << 16
    archive.writestr(info, source.read_bytes())


def build_archive(source: Path, binary: Path, architecture: str, output: Path) -> None:
    if architecture not in SUPPORTED_ARCHITECTURES:
        raise ValueError(f"Unsupported KOReader architecture: {architecture}")
    if not binary.is_file():
        raise FileNotFoundError(f"Receiver binary was not found: {binary}")

    lua_dir = source / "lua"
    required = [lua_dir / "main.lua", lua_dir / "_meta.lua"]
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required plugin file was not found: {missing[0]}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        for path in sorted(lua_dir.glob("*.lua")):
            _write_file(archive, path, f"{PLUGIN_FOLDER}/{path.name}")
        for path in sorted((lua_dir / "locale").rglob("*")):
            if path.is_file():
                relative = path.relative_to(lua_dir).as_posix()
                _write_file(archive, path, f"{PLUGIN_FOLDER}/{relative}")
        for name in ("LICENSE", "LICENSE.upstream", "THIRD_PARTY_NOTICES.md", "README.md"):
            path = source / name
            if path.is_file():
                _write_file(archive, path, f"{PLUGIN_FOLDER}/{name}")
        _write_file(
            archive,
            binary,
            f"{PLUGIN_FOLDER}/localsend",
            executable=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("koreader-plugin"))
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--arch", choices=sorted(SUPPORTED_ARCHITECTURES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_archive(args.source.resolve(), args.binary.resolve(), args.arch, args.output.resolve())


if __name__ == "__main__":
    main()
