#!/usr/bin/env bash
# Reticle installer — sets up the `scancode` CLI in ~/.local/bin with a
# self-contained Python venv under ~/.local/share/reticle.
#
#   ./install.sh            install / update scancode
#   ./install.sh --uninstall remove scancode and its venv
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin"
SHARE="$HOME/.local/share/reticle"
PYBIN="${PYTHON:-python3}"

if [ "${1:-}" = "--uninstall" ]; then
  rm -f "$BIN/scancode"
  rm -rf "$SHARE"
  echo ">> removed scancode and $SHARE"
  exit 0
fi

command -v "$PYBIN" >/dev/null 2>&1 || { echo "!! $PYBIN not found" >&2; exit 1; }

mkdir -p "$BIN" "$SHARE"

if [ ! -x "$SHARE/venv/bin/python" ]; then
  echo ">> creating venv at $SHARE/venv"
  "$PYBIN" -m venv "$SHARE/venv"
fi
echo ">> installing Python deps (zxing-cpp, numpy, opencv-headless)"
"$SHARE/venv/bin/pip" install -q --upgrade pip
"$SHARE/venv/bin/pip" install -q -r "$SRC/requirements.txt"

install -m 0644 "$SRC/lib/scancode.py" "$SHARE/scancode.py"
install -m 0755 "$SRC/bin/scancode"    "$BIN/scancode"
echo ">> installed scancode -> $BIN/scancode"

case ":$PATH:" in
  *":$BIN:"*) ;;
  *)
    for rc in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile"; do
      [ -e "$rc" ] || continue
      grep -q '\.local/bin' "$rc" && continue
      printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$rc"
      echo ">> added ~/.local/bin to PATH in $rc"
    done
    echo ">> open a new shell for PATH to take effect"
    ;;
esac

echo ">> done. Try: scancode --formats"
