#!/usr/bin/env bash
set -euo pipefail

readonly MARKER="X-Spectacle-Toolbelt-Owned=true"
readonly DESKTOP_FILES=(
  "org.kde.spectacle.desktop"
  "io.github.ryanwinkler.spectacle-toolbelt.desktop"
  "io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop"
  "io.github.ryanwinkler.spectacle-toolbelt-web-fullpage.desktop"
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

is_toolbelt_owned() {
  local target=$1
  grep -Fqx "$MARKER" "$target" 2>/dev/null || grep -Fqx "# $MARKER" "$target" 2>/dev/null
}

refresh_kde_cache() {
  local cache_tool=""
  if command -v kbuildsycoca6 >/dev/null 2>&1; then
    cache_tool=$(command -v kbuildsycoca6)
  elif command -v kbuildsycoca5 >/dev/null 2>&1; then
    cache_tool=$(command -v kbuildsycoca5)
  fi

  if [[ -z "$cache_tool" ]]; then
    printf 'KDE service cache refresh skipped: kbuildsycoca6/kbuildsycoca5 not found.\n'
    return 0
  fi

  if [[ "$dry_run" == "true" ]]; then
    print_cmd "$cache_tool"
    return 0
  fi

  if "$cache_tool" >/dev/null 2>&1; then
    printf 'Refreshed KDE service cache with %s\n' "$cache_tool"
  else
    printf 'Warning: KDE service cache refresh failed with %s; run it manually if menus do not disappear.\n' "$cache_tool" >&2
  fi
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

data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
applications_dir="$data_home/applications"
service_menu_dirs=(
  "$data_home/kio/servicemenus"
  "$data_home/kservices5/ServiceMenus"
)
wrapper_file="$data_home/spectacle-toolbelt/bin/spectacle-toolbelt"

for file in "${DESKTOP_FILES[@]}"; do
  target_file="$applications_dir/$file"

  if [[ ! -e "$target_file" ]]; then
    printf 'Not installed: %s\n' "$target_file"
    continue
  fi

  if ! is_toolbelt_owned "$target_file"; then
    printf 'Refusing to remove non-Toolbelt file: %s\n' "$target_file" >&2
    exit 1
  fi

  run rm -f "$target_file"
done

for service_menus_dir in "${service_menu_dirs[@]}"; do
  for file in "${SERVICE_MENU_FILES[@]}"; do
    target_file="$service_menus_dir/$file"

    if [[ ! -e "$target_file" ]]; then
      printf 'Not installed: %s\n' "$target_file"
      continue
    fi

    if ! is_toolbelt_owned "$target_file"; then
      printf 'Refusing to remove non-Toolbelt file: %s\n' "$target_file" >&2
      exit 1
    fi

    run rm -f "$target_file"
  done
done

if [[ -e "$wrapper_file" ]]; then
  if ! is_toolbelt_owned "$wrapper_file"; then
    printf 'Refusing to remove non-Toolbelt file: %s\n' "$wrapper_file" >&2
    exit 1
  fi
  run rm -f "$wrapper_file"
  rmdir "$data_home/spectacle-toolbelt/bin" "$data_home/spectacle-toolbelt" 2>/dev/null || true
else
  printf 'Not installed: %s\n' "$wrapper_file"
fi

printf 'Removed Spectacle Toolbelt desktop entries from %s\n' "$applications_dir"
for service_menus_dir in "${service_menu_dirs[@]}"; do
  printf 'Removed Spectacle Toolbelt service menus from %s\n' "$service_menus_dir"
done
refresh_kde_cache
