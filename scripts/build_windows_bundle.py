"""Build the Windows release ZIP with cmd.exe-compatible batch files."""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def normalize_batch_line_endings(data: bytes) -> bytes:
    """Return batch-file bytes using CRLF on every line."""
    normalized = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return normalized.replace(b"\n", b"\r\n")


def tracked_files(repo_root: Path) -> list[Path]:
    """Return paths tracked by Git, relative to the repository root."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    return [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]


def create_windows_bundle(
    repo_root: Path,
    output_path: Path,
    *,
    files: Iterable[Path] | None = None,
    prefix: str = "pdf-to-epub-ocr",
) -> None:
    """Archive tracked project files and normalize Windows batch launchers."""
    selected_files = list(files) if files is not None else tracked_files(repo_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(output_path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for relative_path in selected_files:
            source_path = repo_root / relative_path
            data = source_path.read_bytes()
            if source_path.suffix.lower() == ".bat":
                data = normalize_batch_line_endings(data)
                if b"\n" in data.replace(b"\r\n", b""):
                    raise ValueError(f"Bare LF remained in batch file: {relative_path}")

            archive_name = str(PurePosixPath(prefix) / PurePosixPath(relative_path.as_posix()))
            info = ZipInfo(archive_name)
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compress_type=ZIP_DEFLATED, compresslevel=9)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    create_windows_bundle(repo_root, args.output.resolve())
    print(f"Created Windows bundle: {args.output.resolve()}")


if __name__ == "__main__":
    main()
