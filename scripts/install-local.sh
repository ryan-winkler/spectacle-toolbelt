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
readonly SERVICE_MENU_FILES=(
  "io.github.ryanwinkler.spectacle-toolbelt-open-in-spectacle.desktop"
  "io.github.ryanwinkler.spectacle-toolbelt-stitch.desktop"
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
service_menu_dirs=(
  "$data_home/kio/servicemenus"
  "$data_home/kservices5/ServiceMenus"
)

run install -d "$applications_dir"
for service_menus_dir in "${service_menu_dirs[@]}"; do
  run install -d "$service_menus_dir"
done

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

for service_menus_dir in "${service_menu_dirs[@]}"; do
  for file in "${SERVICE_MENU_FILES[@]}"; do
    source_file="$repo_root/servicemenus/$file"
    target_file="$service_menus_dir/$file"

    if [[ ! -f "$source_file" ]]; then
      printf 'Missing source service menu file: %s\n' "$source_file" >&2
      exit 1
    fi

    require_owned_or_absent "$target_file"
    run install -m 0644 "$source_file" "$target_file"
  done
done

printf 'Installed Spectacle Toolbelt desktop entries to %s\n' "$applications_dir"
for service_menus_dir in "${service_menu_dirs[@]}"; do
  printf 'Installed Spectacle Toolbelt service menus to %s\n' "$service_menus_dir"
done
printf 'KDE should pick these up automatically; run kbuildsycoca6 manually if your launcher cache is stale.\n'
