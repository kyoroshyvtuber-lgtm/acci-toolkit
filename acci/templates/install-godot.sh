#!/usr/bin/env bash
# Pinned official standard (non-.NET) editor; checks release asset SHA-256.
# No templates or license activation downloaded implicitly.
set -euo pipefail
VERSION=4.7.2
TEMPLATES=false
if [[ "${1:-}" == "--templates" && "$#" == 1 ]]; then
  TEMPLATES=true
elif [[ "$#" != 0 ]]; then
  echo "Usage: install-godot.sh [--templates] (large optional official export archive)" >&2
  exit 2
fi
ROOT="${ACCI_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/acci}/opt/godot-$VERSION"
case "$(uname -s)/$(uname -m)" in
  Linux/x86_64)
    FILE="Godot_v${VERSION}-stable_linux.x86_64.zip"
    SHA256=cadd3204e728a35d3f13adb7fd0d7902636b79f6b95c40c265eb73b6c35329e4
    BINARY="Godot_v${VERSION}-stable_linux.x86_64" ;;
  Darwin/*)
    FILE="Godot_v${VERSION}-stable_macos.universal.zip"
    SHA256=c58a24e31d720be9d62f60cb5627c4e695fb72f21b0cfe1bc9ccaa9a3b3ba63e
    BINARY="Godot.app/Contents/MacOS/Godot" ;;
  *) echo "Use the official editor for your OS/architecture." >&2; exit 2 ;;
esac
mkdir -p "$ROOT"
TMP="$(mktemp -d "$ROOT/.download.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
curl -fL --retry 0 --max-time 300 \
  "https://github.com/godotengine/godot-builds/releases/download/${VERSION}-stable/$FILE" \
  -o "$TMP/editor.zip"
python3 - "$TMP/editor.zip" "$SHA256" <<'PY'
import hashlib, pathlib, sys
digest = hashlib.sha256()
with pathlib.Path(sys.argv[1]).open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
actual = digest.hexdigest()
if actual != sys.argv[2]:
    raise SystemExit("Godot checksum mismatch; refusing to install")
print("Official editor asset SHA-256 verified")
PY
unzip -q -o "$TMP/editor.zip" -d "$ROOT"
chmod +x "$ROOT/$BINARY"
ln -sfn "$ROOT/$BINARY" "$ROOT/godot"
"$ROOT/godot" --headless --version
if [[ "$TEMPLATES" == true ]]; then
  # Opt-in ~1.3 GB download; standard engine, not the .NET export templates.
  curl -fL --retry 0 --max-time 600 \
    "https://github.com/godotengine/godot-builds/releases/download/${VERSION}-stable/Godot_v${VERSION}-stable_export_templates.tpz" \
    -o "$TMP/export.tpz"
  python3 - "$TMP/export.tpz" <<'PY'
import hashlib, pathlib, sys
digest = hashlib.sha256()
with pathlib.Path(sys.argv[1]).open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
if digest.hexdigest() != "f298490b8d44d934be425a5a65a51bf15f422428b229a06a6e11d9ffea248011":
    raise SystemExit("Godot export-template checksum mismatch")
print("Official export templates SHA-256 verified")
PY
  case "$(uname -s)" in
    Darwin) TEMPLATE_ROOT="$HOME/Library/Application Support/Godot/export_templates" ;;
    *) TEMPLATE_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/godot/export_templates" ;;
  esac
  unzip -q "$TMP/export.tpz" -d "$TMP/export"
  [[ "$(tr -d '\r\n' < "$TMP/export/templates/version.txt")" == "${VERSION}.stable" ]] || {
    echo "Unexpected template version" >&2; exit 2;
  }
  mkdir -p "$TEMPLATE_ROOT/${VERSION}.stable"
  cp -R "$TMP/export/templates/." "$TEMPLATE_ROOT/${VERSION}.stable/"
fi
printf 'Editor: %s/godot\nExport templates are separate; see docs/GAMES.md.\n' "$ROOT"