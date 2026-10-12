#!/usr/bin/env bash
#
# REBUILD Strategist — one-command installer.
#
#   curl -fsSL https://raw.githubusercontent.com/Pacino101/rebuild-strategist/main/install.sh | bash
#
# What it does:
#   1. checks Python >= 3.9
#   2. downloads the latest release (no git required) into $REBUILD_DIR
#   3. runs the test suite to verify the install
#   4. optionally installs the DeepSeek Harness skill if ~/.dsh exists
#
# Environment overrides:
#   REBUILD_DIR       install location        (default: $HOME/.rebuild-strategist)
#   REBUILD_VERSION   release tag to fetch    (default: latest)
#   REBUILD_NO_SKILL  set to 1 to skip skill installation
#
set -euo pipefail

REPO="Pacino101/rebuild-strategist"
REBUILD_DIR="${REBUILD_DIR:-$HOME/.rebuild-strategist}"
REBUILD_VERSION="${REBUILD_VERSION:-latest}"
SKILL_DIR="$HOME/.dsh/skills/rebuild-strategist"

info()  { printf '  %s\n' "$*"; }
ok()    { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn()  { printf '  \033[33m!\033[0m %s\n' "$*"; }
die()   { printf '  \033[31m✗\033[0m %s\n' "$*" >&2; exit 1; }

printf '\nREBUILD Strategist — installer\n\n'

# ---------------------------------------------------------------- 1. Python
PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      PY="$candidate"; break
    fi
  fi
done

if [ -z "$PY" ]; then
  found="$(command -v python3 >/dev/null 2>&1 && python3 -V 2>&1 || echo 'not found')"
  die "Python 3.9+ is required (found: $found). Install it from https://www.python.org/downloads/ and re-run."
fi
ok "Python: $($PY -V 2>&1)"

# ------------------------------------------------------- 2. Fetch the source
command -v curl >/dev/null 2>&1 || die "curl is required but not installed."
command -v tar  >/dev/null 2>&1 || die "tar is required but not installed."

if [ "$REBUILD_VERSION" = "latest" ]; then
  # Resolve the latest tag via the GitHub API; fall back to main if unavailable.
  TAG="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null \
         | "$PY" -c 'import json,sys; print(json.load(sys.stdin).get("tag_name",""))' 2>/dev/null || true)"
  [ -z "$TAG" ] && { TAG="main"; warn "No release found; falling back to the main branch."; }
else
  TAG="$REBUILD_VERSION"
fi

if [ "$TAG" = "main" ]; then
  ARCHIVE_URL="https://github.com/$REPO/archive/refs/heads/main.tar.gz"
else
  ARCHIVE_URL="https://github.com/$REPO/archive/refs/tags/$TAG.tar.gz"
fi

info "Downloading $TAG ..."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if ! curl -fsSL "$ARCHIVE_URL" -o "$TMP/src.tar.gz"; then
  die "Download failed: $ARCHIVE_URL
Check your network, or clone instead:
  git clone https://github.com/$REPO.git"
fi

tar -xzf "$TMP/src.tar.gz" -C "$TMP"
SRC="$(find "$TMP" -maxdepth 1 -mindepth 1 -type d | head -1)"
[ -n "$SRC" ] || die "Could not unpack the archive."

if [ -e "$REBUILD_DIR" ]; then
  BACKUP="$REBUILD_DIR.bak.$(date +%Y%m%d-%H%M%S)"
  warn "$REBUILD_DIR already exists; moving it to $BACKUP"
  mv "$REBUILD_DIR" "$BACKUP"
fi
mkdir -p "$(dirname "$REBUILD_DIR")"
cp -R "$SRC" "$REBUILD_DIR"
ok "Installed to $REBUILD_DIR"

# --------------------------------------------------------- 3. Verify it runs
printf '\nVerifying (running the test suite)...\n'
cd "$REBUILD_DIR"
if "$PY" -m unittest discover -s tests >/tmp/rebuild-tests.log 2>&1; then
  COUNT="$("$PY" -m unittest discover -s tests 2>&1 | grep -oE 'Ran [0-9]+ tests' | grep -oE '[0-9]+' || echo '?')"
  ok "$COUNT tests passed"
else
  warn "Test suite reported failures. Last lines:"
  tail -20 /tmp/rebuild-tests.log | sed 's/^/    /'
  warn "The install is in place but did not verify cleanly."
fi

if "$PY" core/rebuild_cli.py validate examples/metro_apartment/project.json >/dev/null 2>&1; then
  ok "CLI works; the worked case validates"
else
  warn "CLI validation did not pass — please open an issue."
fi

# ------------------------------------------------- 4. Optional: host skill
if [ "${REBUILD_NO_SKILL:-0}" != "1" ] && [ -d "$HOME/.dsh" ]; then
  printf '\nDeepSeek Harness detected — installing the skill...\n'
  mkdir -p "$SKILL_DIR"
  cp "$REBUILD_DIR/harness/deepseek/SKILL.md" "$SKILL_DIR/SKILL.md"
  ok "Skill installed at $SKILL_DIR"
  info "It becomes available on the next model step; no restart needed."
else
  info "Skipped host skill installation."
fi

# ------------------------------------------------------------------ Done
cat <<EOF

Done.

  Install location : $REBUILD_DIR
  Run the CLI      : $PY $REBUILD_DIR/core/rebuild_cli.py --help

Try it (no API key, no network):

  $PY $REBUILD_DIR/core/rebuild_cli.py validate \\
      $REBUILD_DIR/examples/metro_apartment/project.json

  $PY $REBUILD_DIR/core/rebuild_cli.py run \\
      $REBUILD_DIR/examples/metro_apartment --dry-run

Reproduce the worked case study (every number in it):

  cd $REBUILD_DIR/examples/metro_apartment/rebuild && $PY scripts/run_all.py

To use a real model, export an API key and add --provider:

  export DEEPSEEK_API_KEY=sk-xxx
  $PY $REBUILD_DIR/core/rebuild_cli.py run <project> --provider deepseek

Docs: https://github.com/$REPO

EOF
