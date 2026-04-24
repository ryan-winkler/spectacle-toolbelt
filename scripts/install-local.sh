#!/usr/bin/env bash
set -euo pipefail

readonly MARKER="X-Spectacle-Toolbelt-Owned=true"
readonly DESKTOP_FILES=(
  "io.github.ryanwinkler.spectacle-toolbelt.desktop"
  "io.github.ryanwinkler.spectacle-toolbelt-scroll.desktop"
  "io.github.ryanwinkler.spectacle-toolbelt-web-fullpage.desktop"
)
readonly SPECTACLE_DESKTOP_FILE="org.kde.spectacle.desktop"
readonly LEGACY_DESKTOP_FILES=(
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

remove_owned_if_present() {
  local target=$1

  if [[ ! -e "$target" ]]; then
    return 0
  fi

  if grep -Fqx "$MARKER" "$target"; then
    run rm -f "$target"
    return 0
  fi

  printf 'Leaving non-Toolbelt file in place: %s\n' "$target" >&2
}

resolve_toolbelt_command() {
  local candidate=${SPECTACLE_TOOLBELT_COMMAND:-}

  if [[ -n "$candidate" ]]; then
    if [[ "$candidate" == */* ]]; then
      if [[ ! -x "$candidate" ]]; then
        printf 'Configured SPECTACLE_TOOLBELT_COMMAND is not executable: %s\n' "$candidate" >&2
        return 1
      fi
      printf '%s\n' "$candidate"
      return 0
    fi

    if ! command -v "$candidate" >/dev/null 2>&1; then
      printf 'Configured SPECTACLE_TOOLBELT_COMMAND is not on PATH: %s\n' "$candidate" >&2
      return 1
    fi
    command -v "$candidate"
    return 0
  fi

  if [[ -x "$repo_root/.venv/bin/spectacle-toolbelt" ]]; then
    printf '%s\n' "$repo_root/.venv/bin/spectacle-toolbelt"
    return 0
  fi

  if command -v spectacle-toolbelt >/dev/null 2>&1; then
    command -v spectacle-toolbelt
    return 0
  fi

  printf 'Could not find spectacle-toolbelt. Run the README local install first: python -m pip install -e '\''.[dev]'\''\n' >&2
  return 1
}

rewrite_exec_lines() {
  local source_file=$1
  local output_file=$2
  local command_path=$3

  awk -v command_path="$command_path" '
    /^Exec=spectacle-toolbelt([[:space:]]|$)/ {
      print "Exec=" command_path substr($0, length("Exec=spectacle-toolbelt") + 1)
      next
    }
    { print }
  ' "$source_file" > "$output_file"
}

rewrite_spectacle_app_actions() {
  local source_file=$1
  local output_file=$2
  local command_path=$3

  awk -v command_path="$command_path" -v marker="$MARKER" '
    function has_action(actions, action) {
      return actions ~ "(^|;)" action "(;|$)"
    }

    /^Actions=/ {
      actions = substr($0, length("Actions=") + 1)
      if (actions != "" && actions !~ /;$/) {
        actions = actions ";"
      }
      if (!has_action(actions, "ToolbeltScrollCapture")) {
        actions = actions "ToolbeltScrollCapture;"
      }
      if (!has_action(actions, "ToolbeltWebFullpage")) {
        actions = actions "ToolbeltWebFullpage;"
      }
      print "Actions=" actions
      actions_seen = 1
      next
    }

    /^X-Spectacle-Toolbelt-Owned=/ {
      next
    }

    { print }

    END {
      if (!actions_seen) {
        print "Actions=ToolbeltScrollCapture;ToolbeltWebFullpage;"
      }
      print ""
      print "[Desktop Action ToolbeltScrollCapture]"
      print "Name=Scrolling Capture"
      print "Exec=" command_path " scroll"
      print ""
      print "[Desktop Action ToolbeltWebFullpage]"
      print "Name=Full-Page Web Capture"
      print "Exec=" command_path " web-fullpage"
      print "X-KDE-Shortcuts=Ctrl+Alt+W"
      print ""
      print marker
    }
  ' "$source_file" > "$output_file"
}

desktop_exec_command() {
  local command_path=$1
  if [[ "$command_path" != *[[:space:]]* ]]; then
    printf '%s\n' "$command_path"
    return 0
  fi

  local escaped=${command_path//\\/\\\\}
  escaped=${escaped//\"/\\\"}
  printf '"%s"\n' "$escaped"
}

install_entry_file() {
  local source_file=$1
  local target_file=$2
  local exec_command=$3

  require_owned_or_absent "$target_file"
  if [[ "$dry_run" == "true" ]]; then
    print_cmd install -m 0644 "$source_file" "$target_file"
    printf 'DRY-RUN: rewrite Exec=spectacle-toolbelt to Exec=%s in %s\n' "$exec_command" "$target_file"
    return 0
  fi

  local temp_file
  temp_file=$(mktemp)
  if ! rewrite_exec_lines "$source_file" "$temp_file" "$exec_command"; then
    rm -f "$temp_file"
    return 1
  fi
  if ! install -m 0644 "$temp_file" "$target_file"; then
    rm -f "$temp_file"
    return 1
  fi
  rm -f "$temp_file"
}

resolve_spectacle_desktop_source() {
  local configured=${SPECTACLE_DESKTOP_SOURCE:-}

  if [[ -n "$configured" ]]; then
    if [[ ! -f "$configured" ]]; then
      printf 'Configured SPECTACLE_DESKTOP_SOURCE does not exist: %s\n' "$configured" >&2
      return 1
    fi
    printf '%s\n' "$configured"
    return 0
  fi

  local candidate
  for candidate in \
    "/usr/share/applications/$SPECTACLE_DESKTOP_FILE" \
    "/usr/local/share/applications/$SPECTACLE_DESKTOP_FILE"; do
    if [[ -f "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 2
}

install_spectacle_app_actions() {
  local target_file=$1
  local exec_command=$2
  local source_file

  local status
  if source_file=$(resolve_spectacle_desktop_source); then
    status=0
  else
    status=$?
  fi
  if [[ "$status" -ne 0 ]]; then
    if [[ "$status" -eq 2 ]]; then
      printf 'Spectacle desktop file not found; skipping Spectacle app action integration.\n'
      return 0
    fi
    return 1
  fi

  require_owned_or_absent "$target_file"
  if [[ "$dry_run" == "true" ]]; then
    print_cmd install -m 0644 "$source_file" "$target_file"
    printf 'DRY-RUN: add Toolbelt Spectacle app actions to %s\n' "$target_file"
    return 0
  fi

  local temp_file
  temp_file=$(mktemp)
  if ! rewrite_spectacle_app_actions "$source_file" "$temp_file" "$exec_command"; then
    rm -f "$temp_file"
    return 1
  fi
  if ! install -m 0644 "$temp_file" "$target_file"; then
    rm -f "$temp_file"
    return 1
  fi
  rm -f "$temp_file"
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
    printf 'Warning: KDE service cache refresh failed with %s; run it manually if menus do not appear.\n' "$cache_tool" >&2
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

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
source_dir="$repo_root/desktop"
toolbelt_command=$(resolve_toolbelt_command)
toolbelt_exec=$(desktop_exec_command "$toolbelt_command")
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

  install_entry_file "$source_file" "$target_file" "$toolbelt_exec"
done

install_spectacle_app_actions "$applications_dir/$SPECTACLE_DESKTOP_FILE" "$toolbelt_exec"

for file in "${LEGACY_DESKTOP_FILES[@]}"; do
  remove_owned_if_present "$applications_dir/$file"
done

for service_menus_dir in "${service_menu_dirs[@]}"; do
  for file in "${SERVICE_MENU_FILES[@]}"; do
    source_file="$repo_root/servicemenus/$file"
    target_file="$service_menus_dir/$file"

    if [[ ! -f "$source_file" ]]; then
      printf 'Missing source service menu file: %s\n' "$source_file" >&2
      exit 1
    fi

    install_entry_file "$source_file" "$target_file" "$toolbelt_exec"
  done
done

printf 'Installed Spectacle Toolbelt launcher to %s\n' "$applications_dir"
printf 'Installed Spectacle launcher app actions to %s/%s\n' "$applications_dir" "$SPECTACLE_DESKTOP_FILE"
printf 'Cleaned up legacy Spectacle Toolbelt desktop launchers from %s\n' "$applications_dir"
for service_menus_dir in "${service_menu_dirs[@]}"; do
  printf 'Installed Spectacle Toolbelt service menus to %s\n' "$service_menus_dir"
done
printf 'Installed entries use Toolbelt command: %s\n' "$toolbelt_command"
refresh_kde_cache
