#!/usr/bin/env bash
set -euo pipefail

# Usage:
#  - Dry-run (package only): ./scripts/publish_marketplace.sh
#  - Publish (requires PAT env var): PUBLISH=1 PAT=ghp_xxx ./scripts/publish_marketplace.sh

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

MARKET_README="README.marketplace.md"
README="README.md"

if [ ! -f "$MARKET_README" ]; then
  echo "Error: $MARKET_README not found. Create it or run from repo root." >&2
  exit 1
fi

TMP_README="$(mktemp --suffix=.README.backup 2>/dev/null || mktemp)"
TMP_PKG="$(mktemp --suffix=.package.json.backup 2>/dev/null || mktemp)"

echo "Backing up current README and package.json"
cp "$README" "$TMP_README"
cp package.json "$TMP_PKG"

echo "Replacing $README with $MARKET_README for packaging"
cp "$MARKET_README" "$README"

echo "Bumping patch version in package.json"
orig_version=$(node -e "console.log(require('./package.json').version)")
new_version=$(node -e "let p=require('./package.json'); let v=p.version.split('.'); v[2]=String((Number(v[2]||0)+1)); p.version=v.join('.'); require('fs').writeFileSync('package.json', JSON.stringify(p,null,2)+'\n'); console.log(p.version);")
echo "Version: $orig_version -> $new_version"

echo "Packaging extension (this will create a .vsix in the repo root)"
npx -y @vscode/vsce package

if [ "${PUBLISH:-0}" != "0" ]; then
  if [ -z "${PAT:-}" ]; then
    echo "PAT is not set. Export PAT environment variable and re-run with PUBLISH=1 to publish." >&2
  else
    echo "Publishing to Marketplace with provided PAT"
    npx -y @vscode/vsce publish --pat "$PAT"
  fi
else
  echo "Skipped publishing. To publish set PUBLISH=1 and provide PAT env var."
fi

echo "Restoring original README and package.json"
mv "$TMP_README" "$README"
mv "$TMP_PKG" package.json

echo "Done. Created VSIX for version $new_version. If you want to publish now, run:"
echo "  PUBLISH=1 PAT=your_token ./scripts/publish_marketplace.sh"
