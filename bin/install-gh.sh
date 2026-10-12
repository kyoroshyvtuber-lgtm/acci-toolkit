#!/usr/bin/env bash
# Install the official GitHub CLI into $ACCI_HOME/opt with SHA-256 verification.
set -euo pipefail
ACCI_HOME="${ACCI_HOME:-/data/acci}"; mkdir -p "$ACCI_HOME/opt" && cd "$ACCI_HOME/opt"
TAG=$(curl -fsS https://api.github.com/repos/cli/cli/releases/latest | python3 -c 'import sys,json;print(json.load(sys.stdin)["tag_name"])')
V=${TAG#v}; F=gh_${V}_linux_amd64.tar.gz
curl -fsSLO "https://github.com/cli/cli/releases/download/$TAG/$F"
curl -fsSLO "https://github.com/cli/cli/releases/download/$TAG/gh_${V}_checksums.txt"
grep " $F\$" "gh_${V}_checksums.txt" | sha256sum -c -
tar xzf "$F" && ln -sfn "$ACCI_HOME/opt/gh_${V}_linux_amd64/bin/gh" "$ACCI_HOME/opt/gh" && "$ACCI_HOME/opt/gh" --version | head -1
