#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${1:-}" == "--self-test" ]]; then
  echo "PDF_TO_EPUB_UNIX_LAUNCHER_OK"
  exit 0
fi

case "$(uname -s)" in
  Linux) install_root="${XDG_DATA_HOME:-$HOME/.local/share}/pdf-to-epub-ocr" ;;
  Darwin) install_root="$HOME/Library/Application Support/PDF-to-EPUB-OCR" ;;
  *) echo "Unsupported operating system." >&2; exit 1 ;;
esac

gui="$install_root/venv/bin/pdf-to-epub-gui"
if [[ ! -x "$gui" ]]; then
  echo "PDF to EPUB OCR is not installed. Run ./setup.sh first." >&2
  exit 1
fi
exec "$gui" "$@"
