#!/bin/sh
set -e

repo_root=$(cd "$(dirname "$0")/.." && pwd)
hooks_src="$repo_root/.githooks"
hooks_dst="$repo_root/.git/hooks"

mkdir -p "$hooks_dst"

for hook in "$hooks_src"/*; do
  [ -f "$hook" ] || continue
  name=$(basename "$hook")
  cp "$hook" "$hooks_dst/$name"
  chmod +x "$hooks_dst/$name"
  echo "Installed $name"
done
