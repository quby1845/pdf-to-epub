"""Build portable Linux/macOS source bundles with executable launchers."""

from __future__ import annotations

import argparse
import stat
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

UNIX_FILES = (
    Path("setup.sh"),
    Path("launch.sh"),
    Path("pyproject.toml"),
    Path("README.md"),
    Path("README_TR.md"),
    Path("CHANGELOG.md"),
    Path("LICENSE"),
    Path("src"),
)


def _iter_files(repo: Path, entries: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for entry in entries:
        source = repo / entry
        files.extend(
            sorted(path for path in source.rglob("*") if path.is_file())
            if source.is_dir()
            else [source]
        )
    return files


def create_unix_bundle(repo: Path, output: Path, *, platform: str) -> None:
    """Create a ZIP that preserves executable bits on setup and launch scripts."""
    if platform not in {"linux", "macos"}:
        raise ValueError(f"Unsupported bundle platform: {platform}")
    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = f"pdf-to-epub-ocr-{platform}"
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for source in _iter_files(repo, UNIX_FILES):
            relative = source.relative_to(repo)
            info = ZipInfo((Path(prefix) / relative).as_posix())
            info.create_system = 3
            mode = 0o755 if relative in {Path("setup.sh"), Path("launch.sh")} else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, source.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=("linux", "macos"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    create_unix_bundle(Path(__file__).resolve().parents[1], args.output, platform=args.platform)
    print(f"Created {args.platform} bundle: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
