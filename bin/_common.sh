#!/usr/bin/env bash
# Shared by the orchestrator-only helpers. Do not source from project commands.
if [[ -z "${ACCI_HOME:-}" ]]; then
  if [[ -d /data && -w /data ]]; then ACCI_HOME=/data/acci
  else ACCI_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/acci"; fi
fi
export ACCI_HOME
export GH_CONFIG_DIR="${ACCI_GH_CONFIG_DIR:-${GH_CONFIG_DIR:-$ACCI_HOME/secrets/gh}}"
export GH_PROMPT_DISABLED=1 GH_NO_UPDATE_NOTIFIER=1

acci_find_gh() {
  if [[ -n "${ACCI_GH:-}" ]]; then ACCI_GH_BIN="$ACCI_GH"
  elif [[ -x "$ACCI_HOME/opt/gh" ]]; then ACCI_GH_BIN="$ACCI_HOME/opt/gh"
  else ACCI_GH_BIN="$(command -v gh || true)"; fi
  if [[ -z "$ACCI_GH_BIN" || ! -x "$ACCI_GH_BIN" ]]; then
    echo "ACCI: gh is missing. Install GitHub CLI or run bin/install-gh.sh." >&2
    return 127
  fi
}