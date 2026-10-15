#!/usr/bin/env bash
# Install the official GitHub CLI into $ACCI_HOME/opt with SHA-256 verification.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
[[ "$(uname -s)" == Linux ]] || { echo "Install GitHub CLI for your OS; this helper supports Linux." >&2; exit 2; }
case "$(uname -m)" in
  x86_64) ARCH=amd64 ;;
  aarch64|arm64) ARCH=arm64 ;;
  *) echo "Unsupported architecture; install GitHub CLI manually." >&2; exit 2 ;;
esac
mkdir -p "$ACCI_HOME/opt"
TMP="$(mktemp -d "$ACCI_HOME/opt/.gh-download.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
cd "$TMP"
TAG=$(curl -fsS --max-time 60 https://api.github.com/repos/cli/cli/releases/latest |
  python3 -c 'import sys,json,re; t=json.load(sys.stdin)["tag_name"]; assert re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+",t); print(t)')
V=${TAG#v}; F=gh_${V}_linux_${ARCH}.tar.gz
curl -fsSLO --max-time 180 "https://github.com/cli/cli/releases/download/$TAG/$F"
curl -fsSLO --max-time 60 "https://github.com/cli/cli/releases/download/$TAG/gh_${V}_checksums.txt"
python3 - "$F" "gh_${V}_checksums.txt" <<'PY'
import hashlib, pathlib, sys
name, checksums = sys.argv[1:]
matches = [line.split()[0] for line in pathlib.Path(checksums).read_text().splitlines()
           if line.split() and line.split()[-1].lstrip("*") == name]
assert len(matches) == 1, "Expected one release checksum"
assert hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() == matches[0], "Checksum mismatch"
print("SHA-256 verified")
PY
tar xzf "$F" -C "$ACCI_HOME/opt"
ln -sfn "$ACCI_HOME/opt/gh_${V}_linux_${ARCH}/bin/gh" "$ACCI_HOME/opt/gh"
"$ACCI_HOME/opt/gh" --version | head -1
