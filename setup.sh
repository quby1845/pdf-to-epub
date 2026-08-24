#!/usr/bin/env bash
set -Eeuo pipefail

APP_ID="pdf-to-epub-ocr"
APP_NAME="PDF to EPUB OCR"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODE="install"
BACKEND="auto"
SKIP_SYSTEM_PACKAGES=0
ASSUME_YES=0

usage() {
  cat <<'EOF'
PDF to EPUB OCR setup for Linux and macOS

Usage: ./setup.sh [options]
  --check                 Validate the existing installation
  --repair                Reinstall the managed environment
  --uninstall             Remove the app (downloaded OCR models are preserved)
  --backend auto|cuda|rocm
  --skip-system-packages  Do not install Pandoc, Poppler, Tk, or Calibre
  --yes                   Do not ask before installing system packages
  --self-test             Validate this script without changing the computer
EOF
}

while (($#)); do
  case "$1" in
    --check|--repair|--uninstall) MODE="${1#--}" ;;
    --backend) shift; BACKEND="${1:-}" ;;
    --skip-system-packages) SKIP_SYSTEM_PACKAGES=1 ;;
    --yes) ASSUME_YES=1 ;;
    --self-test) echo "PDF_TO_EPUB_UNIX_SETUP_OK"; exit 0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

case "$BACKEND" in auto|cuda|rocm) ;; *) echo "Invalid backend: $BACKEND" >&2; exit 2 ;; esac

OS="$(uname -s)"
case "$OS" in
  Linux)
    DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
    CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
    BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"
    INSTALL_ROOT="$DATA_HOME/$APP_ID"
    ;;
  Darwin)
    INSTALL_ROOT="$HOME/Library/Application Support/PDF-to-EPUB-OCR"
    CONFIG_HOME="$HOME/Library/Application Support"
    BIN_HOME="$HOME/.local/bin"
    ;;
  *) echo "Unsupported operating system: $OS" >&2; exit 1 ;;
esac

VENV="$INSTALL_ROOT/venv"
VENV_PYTHON="$VENV/bin/python"
LAUNCHER="$BIN_HOME/pdf-to-epub-gui"

remove_installation() {
  rm -rf -- "$VENV"
  rm -f -- "$LAUNCHER"
  if [[ "$OS" == Linux ]]; then
    rm -f -- "$HOME/.local/share/applications/pdf-to-epub-ocr.desktop"
  else
    rm -rf -- "$HOME/Applications/PDF to EPUB OCR.app"
  fi
  echo "$APP_NAME was removed. OCR model downloads were preserved in the cache."
}

check_installation() {
  local failed=0
  [[ -x "$VENV_PYTHON" ]] || { echo "Missing managed Python environment: $VENV" >&2; failed=1; }
  if [[ -x "$VENV_PYTHON" ]]; then
    "$VENV_PYTHON" -c "import pdf_to_epub; print('Application:', pdf_to_epub.__version__)" || failed=1
    "$VENV_PYTHON" - <<'PY' || failed=1
try:
    import torch
    print("PyTorch:", torch.__version__)
    print("CUDA/ROCm available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        value = torch.ones(1, device="cuda")
        value.add_(1)
        torch.cuda.synchronize()
        print("GPU:", torch.cuda.get_device_name(0))
except ImportError:
    print("PyTorch: not installed")
PY
  fi
  for tool in pandoc pdfinfo; do
    command -v "$tool" >/dev/null || { echo "Missing command: $tool" >&2; failed=1; }
  done
  return "$failed"
}

if [[ "$MODE" == uninstall ]]; then remove_installation; exit 0; fi
if [[ "$MODE" == check ]]; then check_installation; exit $?; fi

find_python() {
  local candidate version
  for candidate in python3.13 python3.12 python3.11 python3; do
    command -v "$candidate" >/dev/null || continue
    version="$($candidate -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
    case "$version" in 3.11|3.12|3.13) command -v "$candidate"; return 0 ;; esac
  done
  return 1
}

install_system_packages() {
  ((SKIP_SYSTEM_PACKAGES)) && return
  if [[ "$OS" == Darwin ]]; then
    command -v brew >/dev/null || {
      echo "Homebrew is required. Install it from https://brew.sh and run setup.sh again." >&2
      exit 1
    }
    brew install python@3.13 python-tk@3.13 pandoc poppler
    brew list --cask calibre >/dev/null 2>&1 || brew install --cask calibre
    return
  fi

  local yes=()
  ((ASSUME_YES)) && yes=(-y)
  if command -v apt-get >/dev/null; then
    sudo apt-get update
    sudo apt-get install "${yes[@]}" python3 python3-venv python3-tk pandoc poppler-utils calibre
  elif command -v dnf >/dev/null; then
    sudo dnf install "${yes[@]}" python3 python3-tkinter pandoc poppler-utils calibre
  elif command -v pacman >/dev/null; then
    ((ASSUME_YES)) && yes=(--noconfirm)
    sudo pacman -S --needed "${yes[@]}" python tk pandoc poppler calibre
  elif command -v zypper >/dev/null; then
    ((ASSUME_YES)) && yes=(--non-interactive)
    sudo zypper "${yes[@]}" install python3 python3-tk pandoc poppler-tools calibre
  else
    echo "No supported package manager was found. Install Python, Tk, Pandoc, Poppler, and Calibre, then rerun with --skip-system-packages." >&2
    exit 1
  fi
}

detect_backend() {
  if [[ "$OS" == Darwin ]]; then echo "macos"; return; fi
  if [[ "$BACKEND" != auto ]]; then echo "$BACKEND"; return; fi
  if command -v nvidia-smi >/dev/null && nvidia-smi -L >/dev/null 2>&1; then echo "cuda"; return; fi
  if [[ -e /dev/kfd ]] || (command -v rocminfo >/dev/null && rocminfo >/dev/null 2>&1); then echo "rocm"; return; fi
  echo "none"
}

install_cuda_torch() {
  local channel="cu126" gpu_name
  gpu_name="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 || true)"
  [[ "$gpu_name" =~ RTX[[:space:]]50 ]] && channel="cu130"
  echo "Installing NVIDIA PyTorch from the $channel channel for: ${gpu_name:-detected GPU}"
  "$VENV_PYTHON" -m pip install --upgrade --force-reinstall torch torchvision --index-url "https://download.pytorch.org/whl/$channel"
}

install_rocm_torch() {
  [[ "$(uname -m)" == x86_64 ]] || { echo "AMD ROCm setup requires x86_64 Linux." >&2; exit 1; }
  local py_tag
  py_tag="$($VENV_PYTHON -c 'import sys; print(f"cp{sys.version_info.major}{sys.version_info.minor}")')"
  [[ "$py_tag" == cp312 ]] || { echo "AMD ROCm 7.2.1 setup requires Python 3.12." >&2; exit 1; }
  [[ -e /dev/kfd ]] || { echo "ROCm device /dev/kfd was not found. Install the supported AMD Radeon driver and ROCm 7.2.1 first." >&2; exit 1; }
  local base="https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2.1"
  "$VENV_PYTHON" -m pip install --upgrade --force-reinstall \
    "$base/torch-2.9.1%2Brocm7.2.1.lw.gitff65f5bc-cp312-cp312-linux_x86_64.whl" \
    "$base/torchvision-0.24.0%2Brocm7.2.1.gitb919bd0c-cp312-cp312-linux_x86_64.whl" \
    "$base/torchaudio-2.9.0%2Brocm7.2.1.gite3c6ee2b-cp312-cp312-linux_x86_64.whl" \
    "$base/triton-3.5.1%2Brocm7.2.1.gita272dfa8-cp312-cp312-linux_x86_64.whl"
}

create_launchers() {
  mkdir -p -- "$BIN_HOME"
  cat >"$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/pdf-to-epub-gui" "\$@"
EOF
  chmod +x "$LAUNCHER"
  if [[ "$OS" == Linux ]]; then
    local desktop_dir="$HOME/.local/share/applications"
    mkdir -p -- "$desktop_dir"
    cat >"$desktop_dir/pdf-to-epub-ocr.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=PDF to EPUB OCR
Comment=Convert scanned PDF books locally
Exec=$LAUNCHER
Terminal=false
Categories=Office;Utility;
StartupNotify=true
EOF
  else
    local app="$HOME/Applications/PDF to EPUB OCR.app"
    mkdir -p -- "$app/Contents/MacOS"
    cat >"$app/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>PDF to EPUB OCR</string>
<key>CFBundleDisplayName</key><string>PDF to EPUB OCR</string>
<key>CFBundleIdentifier</key><string>io.github.quby1845.pdf-to-epub-ocr</string>
<key>CFBundleVersion</key><string>0.11.0</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleExecutable</key><string>pdf-to-epub-ocr</string>
</dict></plist>
EOF
    cp -- "$LAUNCHER" "$app/Contents/MacOS/pdf-to-epub-ocr"
  fi
}

install_system_packages
PYTHON="$(find_python || true)"
[[ -n "$PYTHON" ]] || { echo "Python 3.11, 3.12, or 3.13 was not found." >&2; exit 1; }

if [[ "$MODE" == repair ]]; then rm -rf -- "$VENV"; fi
if [[ -x "$VENV_PYTHON" ]] && ! "$VENV_PYTHON" -c 'import sys; assert sys.prefix != sys.base_prefix' >/dev/null 2>&1; then
  rm -rf -- "$VENV"
fi
if [[ ! -x "$VENV_PYTHON" ]]; then
  mkdir -p -- "$INSTALL_ROOT"
  "$PYTHON" -m venv "$VENV"
fi
"$VENV_PYTHON" -m pip install --upgrade pip wheel

RUNTIME_BACKEND="$(detect_backend)"
case "$RUNTIME_BACKEND" in
  cuda) install_cuda_torch ;;
  rocm) install_rocm_torch ;;
  macos)
    "$VENV_PYTHON" -m pip install --upgrade torch torchvision
    echo "NOTE: The desktop app is installed on macOS, but the current upstream DeepSeek OCR engine requires CUDA. Apple Silicon/Metal (MPS) conversion is not available yet."
    ;;
  none)
    echo "No supported NVIDIA CUDA or AMD ROCm GPU was detected. The interface can be installed, but local OCR conversion cannot run." >&2
    ;;
esac

"$VENV_PYTHON" -m pip install --upgrade "$SCRIPT_DIR"
create_launchers

if [[ "$RUNTIME_BACKEND" == cuda || "$RUNTIME_BACKEND" == rocm ]]; then
  "$VENV_PYTHON" - <<'PY'
import torch
assert torch.cuda.is_available(), "CUDA/ROCm is unavailable"
value = torch.ones(1, device="cuda")
value.add_(1)
torch.cuda.synchronize()
print("GPU validation passed:", torch.cuda.get_device_name(0))
PY
fi

echo
echo "$APP_NAME installation completed."
if [[ "$OS" == Linux ]]; then
  echo "Open it from the application menu or run: $LAUNCHER"
else
  echo "Open: $HOME/Applications/PDF to EPUB OCR.app"
fi
