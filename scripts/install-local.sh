#!/usr/bin/env bash
set -euo pipefail

readonly MARKER="X-Spectacle-Toolbelt-Owned=true"
readonly DESKTOP_FILES=(
  "io.github.ryanwinkler.spectacle-toolbelt.desktop"
  "io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop"
  "io.github.ryanwinkler.spectacle-toolbelt-transform.desktop"
  "io.github.ryanwinkler.spectacle-toolbelt-redact.desktop"
  "io.github.ryanwinkler.spectacle-toolbelt-copy-markdown.desktop"
)

dry_run=false

usage() {
  printf 'Usage: %s [--dry-run]\n' "$(basename "$0")"
}

print_cmd() {
  printf 'DRY-RUN:'
  printf ' %q' "$@"
  printf '\n'
}

run() {
  if [[ "$dry_run" == "true" ]]; then
    print_cmd "$@"
  else
    "$@"
  fi
}

require_owned_or_absent() {
  local target=$1

  if [[ ! -e "$target" ]]; then
    return 0
  fi

  if grep -Fqx "$MARKER" "$target"; then
    return 0
  fi

  printf 'Refusing to overwrite non-Toolbelt file: %s\n' "$target" >&2
  return 1
}

while (($#)); do
  case "$1" in
    --dry-run)
      dry_run=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
  shift
done

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
source_dir="$repo_root/desktop"
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
applications_dir="$data_home/applications"

run install -d "$applications_dir"

for file in "${DESKTOP_FILES[@]}"; do
  source_file="$source_dir/$file"
  target_file="$applications_dir/$file"

  if [[ ! -f "$source_file" ]]; then
    printf 'Missing source desktop file: %s\n' "$source_file" >&2
    exit 1
  fi

  require_owned_or_absent "$target_file"
  run install -m 0644 "$source_file" "$target_file"
done

printf 'Installed Spectacle Toolbelt desktop entries to %s\n' "$applications_dir"
printf 'KDE should pick these up automatically; run kbuildsycoca6 manually if your launcher cache is stale.\n'
