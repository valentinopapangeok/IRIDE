#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
while IFS=$'\t' read -r directory remote; do
  test "$directory" = directory && continue
  if test -d "$root/$directory/.git"; then
    printf 'exists: %s\n' "$directory"
  else
    git clone "$remote" "$root/$directory"
  fi
done < "$root/products/repositories.tsv"
