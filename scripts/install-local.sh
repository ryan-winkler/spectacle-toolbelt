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

is_toolbelt_owned() {
  local target=$1
  if [[ -L "$target" ]]; then
    return 1
  fi
  grep -Fqx "$MARKER" "$target" 2>/dev/null || grep -Fqx "# $MARKER" "$target" 2>/dev/null
}

require_owned_or_absent() {
  local target=$1

  if [[ ! -e "$target" && ! -L "$target" ]]; then
    return 0
  fi

  if is_toolbelt_owned "$target"; then
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
  local data_home=$1
  local candidate=${SPECTACLE_TOOLBELT_COMMAND:-}
  local command_path

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

  if command_path=$(resolve_existing_toolbelt_command); then
    printf '%s\n' "$command_path"
    return 0
  fi

  ensure_runtime_wrapper "$data_home"
}

resolve_existing_toolbelt_command() {
  local candidate
  for candidate in "$repo_root/.venv/bin/spectacle-toolbelt"; do
    if [[ -x "$candidate" ]]; then
      if is_usable_toolbelt_command "$candidate"; then
        printf '%s\n' "$candidate"
        return 0
      fi
      printf 'Ignoring existing Toolbelt command without required local capture dependencies: %s\n' "$candidate" >&2
    fi
  done

  if command -v spectacle-toolbelt >/dev/null 2>&1; then
    candidate=$(command -v spectacle-toolbelt)
    if is_usable_toolbelt_command "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
    printf 'Ignoring PATH Toolbelt command without required local capture dependencies: %s\n' "$candidate" >&2
  fi

  return 1
}

is_usable_toolbelt_command() {
  local candidate=$1
  local session_type=${XDG_SESSION_TYPE:-}

  if [[ "${session_type,,}" == "wayland" ]]; then
    XDG_SESSION_TYPE=wayland "$candidate" doctor >/dev/null 2>&1
    return $?
  fi

  XDG_SESSION_TYPE=x11 "$candidate" doctor >/dev/null 2>&1
}

quote_sh() {
  local value=$1
  printf "'%s'" "${value//\'/\'\\\'\'}"
}

ensure_runtime_wrapper() {
  local data_home=$1
  local wrapper_dir="$data_home/spectacle-toolbelt/bin"
  local wrapper="$wrapper_dir/spectacle-toolbelt"
  local python_command
  local import_command
  local existing_import_command
  local existing_python_command

  if [[ -z "${SPECTACLE_TOOLBELT_IMPORT_COMMAND:-}" ]]; then
    if existing_import_command=$(owned_wrapper_import_command "$wrapper"); then
      export SPECTACLE_TOOLBELT_IMPORT_COMMAND="$existing_import_command"
    fi
  fi
  existing_python_command=$(owned_wrapper_python_command "$wrapper" || true)

  if ! python_command=$(find_runtime_python "$existing_python_command"); then
    return 1
  fi
  if ! ensure_session_capture_backend; then
    return 1
  fi
  import_command=$(resolve_imagemagick_import_command 2>/dev/null || printf '%s' "${SPECTACLE_TOOLBELT_IMPORT_COMMAND:-import}")

  if [[ "$dry_run" == "true" ]]; then
    {
      printf 'DRY-RUN:'
      printf ' %q' install -d "$wrapper_dir"
      printf '\n'
      printf 'DRY-RUN: write KDE runtime wrapper to %s using %s\n' "$wrapper" "$python_command"
    } >&2
    printf '%s\n' "$wrapper"
    return 0
  fi

  if ! require_owned_or_absent "$wrapper"; then
    return 1
  fi
  install -d "$wrapper_dir"
  local temp_file
  temp_file=$(mktemp)
  {
    printf '#!/usr/bin/env sh\n'
    printf '# %s\n' "$MARKER"
    printf 'export PYTHONPATH=%s${PYTHONPATH:+:$PYTHONPATH}\n' "$(quote_sh "$repo_root/src")"
    printf 'toolbelt_import_command=${SPECTACLE_TOOLBELT_IMPORT_COMMAND:-%s}\n' "$(quote_sh "$import_command")"
    printf 'if [ -z "$toolbelt_import_command" ]; then\n'
    printf '  toolbelt_import_command=import\n'
    printf 'fi\n'
    printf 'export SPECTACLE_TOOLBELT_IMPORT_COMMAND="$toolbelt_import_command"\n'
    printf 'toolbelt_help_only=false\n'
    printf 'for toolbelt_arg in "$@"; do\n'
    printf '  case "$toolbelt_arg" in\n'
    printf '    -h|--help) toolbelt_help_only=true ;;\n'
    printf '  esac\n'
    printf 'done\n'
    printf 'if [ "${1:-}" = "scroll" ] && [ "$toolbelt_help_only" != "true" ]; then\n'
    printf '  case "${XDG_SESSION_TYPE:-}" in\n'
    printf '    wayland|Wayland|WAYLAND)\n'
    printf '      if ! %s -c %s >/dev/null 2>&1; then\n' \
      "$(quote_sh "$python_command")" \
      "$(quote_sh "import dbus")"
    printf '        printf %s %s >&2\n' \
      "$(quote_sh "%s\n")" \
      "$(quote_sh "Spectacle Toolbelt fixed-region capture on Wayland requires dbus-python. Install it, then run spectacle-toolbelt doctor.")"
    printf '        exit 1\n'
    printf '      fi\n'
    printf '      ;;\n'
    printf '    *)\n'
    printf '      case "$toolbelt_import_command" in\n'
    printf '        */*) [ -x "$toolbelt_import_command" ] ;;\n'
    printf '        *) command -v "$toolbelt_import_command" >/dev/null 2>&1 ;;\n'
    printf '      esac\n'
    printf '      if [ $? -ne 0 ]; then\n'
    printf '        printf %s %s >&2\n' \
      "$(quote_sh "%s\n")" \
      "$(quote_sh "Spectacle Toolbelt fixed-region capture on X11/non-Wayland sessions requires ImageMagick import. Install ImageMagick, then run spectacle-toolbelt doctor.")"
    printf '        exit 1\n'
    printf '      fi\n'
    printf '      ;;\n'
    printf '  esac\n'
    printf 'fi\n'
    printf 'exec %s -m spectacle_toolbelt.cli "$@"\n' "$(quote_sh "$python_command")"
  } > "$temp_file"
  install -m 0755 "$temp_file" "$wrapper"
  rm -f "$temp_file"
  printf '%s\n' "$wrapper"
}

owned_wrapper_import_command() {
  local wrapper=$1
  local line
  local value

  if [[ ! -f "$wrapper" || ! -x "$wrapper" ]]; then
    return 1
  fi
  if ! is_toolbelt_owned "$wrapper"; then
    return 1
  fi
  line=$(grep -m1 -F 'toolbelt_import_command=${SPECTACLE_TOOLBELT_IMPORT_COMMAND:-' "$wrapper" || true)
  if [[ -z "$line" ]]; then
    return 1
  fi
  value=${line#*:-}
  value=${value%\}}
  if [[ "$value" == \'*\' ]]; then
    value=${value#\'}
    value=${value%\'}
  fi
  if [[ -z "$value" ]]; then
    return 1
  fi
  printf '%s\n' "$value"
}

owned_wrapper_python_command() {
  local wrapper=$1
  local line
  local value

  if [[ ! -f "$wrapper" || ! -x "$wrapper" ]]; then
    return 1
  fi
  if ! is_toolbelt_owned "$wrapper"; then
    return 1
  fi
  line=$(grep -m1 -F ' -m spectacle_toolbelt.cli "$@"' "$wrapper" || true)
  if [[ -z "$line" ]]; then
    return 1
  fi
  value=${line#exec }
  value=${value% -m spectacle_toolbelt.cli \"\$@\"}
  if [[ "$value" == \'*\' ]]; then
    value=${value#\'}
    value=${value%\'}
  fi
  if [[ -z "$value" ]]; then
    return 1
  fi
  printf '%s\n' "$value"
}

ensure_session_capture_backend() {
  local session_type="${XDG_SESSION_TYPE:-}"
  if [[ "${session_type,,}" == "wayland" ]]; then
    return 0
  fi
  if imagemagick_import_available; then
    return 0
  fi
  printf 'ImageMagick import is required for fixed-region X11/non-Wayland capture.\n' >&2
  printf 'Install ImageMagick or set SPECTACLE_TOOLBELT_COMMAND to a command whose doctor passes.\n' >&2
  return 1
}

imagemagick_import_available() {
  resolve_imagemagick_import_command >/dev/null 2>&1
}

resolve_imagemagick_import_command() {
  local command_name="${SPECTACLE_TOOLBELT_IMPORT_COMMAND:-import}"
  if [[ "$command_name" == */* ]]; then
    if [[ -x "$command_name" ]]; then
      printf '%s\n' "$command_name"
      return 0
    fi
    return 1
  fi
  command -v "$command_name"
}

find_runtime_python() {
  local preferred=${1:-}
  local candidates=()
  local candidate
  if [[ -n "$preferred" ]]; then
    candidates+=("$preferred")
  fi
  if [[ -n "${SPECTACLE_TOOLBELT_PYTHON_CANDIDATES:-}" ]]; then
    local configured_candidates=()
    IFS=: read -r -a configured_candidates <<< "$SPECTACLE_TOOLBELT_PYTHON_CANDIDATES"
    candidates+=("${configured_candidates[@]}")
  else
    for candidate in /usr/bin/python3 /usr/bin/python; do
      candidates+=("$candidate")
    done
    if command -v python3 >/dev/null 2>&1; then
      candidates+=("$(command -v python3)")
    fi
    if command -v python >/dev/null 2>&1; then
      candidates+=("$(command -v python)")
    fi
  fi

  local full_probe_code
  full_probe_code=$(runtime_python_probe true)

  local seen=" "
  for candidate in "${candidates[@]}"; do
    if [[ -z "$candidate" || ! -x "$candidate" || "$seen" == *" $candidate "* ]]; then
      continue
    fi
    seen+="$candidate "
    if "$candidate" -c "$full_probe_code" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  local session_type="${XDG_SESSION_TYPE:-}"
  if [[ "${session_type,,}" != "wayland" ]]; then
    local x11_probe_code
    x11_probe_code=$(runtime_python_probe false)
    seen=" "
    for candidate in "${candidates[@]}"; do
      if [[ -z "$candidate" || ! -x "$candidate" || "$seen" == *" $candidate "* ]]; then
        continue
      fi
      seen+="$candidate "
      if "$candidate" -c "$x11_probe_code" >/dev/null 2>&1; then
        printf 'Warning: selected Python runtime lacks dbus-python; Wayland fixed-region capture will require it.\n' >&2
        printf '%s\n' "$candidate"
        return 0
      fi
    done
  fi

  {
    printf 'Could not find a Python runtime with Pillow, websockets, and GTK 4/PyGObject'
    if [[ "${session_type,,}" == "wayland" ]]; then
      printf ', plus dbus-python for Wayland fixed-region capture'
    fi
    printf '.\n'
  } >&2
  printf 'Install the missing runtime packages or set SPECTACLE_TOOLBELT_COMMAND explicitly.\n' >&2
  return 1
}

runtime_python_probe() {
  local include_dbus=${1:-true}
  printf '%s\n' \
    'import PIL, websockets' \
    'import gi' \
    'gi.require_version("Gtk", "4.0")' \
    'from gi.repository import Gdk, Gtk'
  if [[ "$include_dbus" == "true" ]]; then
    printf '%s\n' 'import dbus'
  fi
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

    function insert_kwin_authorization() {
      if (!kwin_dbus_seen) {
        print "X-KDE-DBUS-Restricted-Interfaces=org.kde.KWin.ScreenShot2"
      }
      if (!kwin_wayland_seen) {
        print "X-KDE-Wayland-Interfaces=org_kde_plasma_window_management,zkde_screencast_unstable_v1"
      }
      kwin_authorization_inserted = 1
    }

    /^X-KDE-DBUS-Restricted-Interfaces=/ {
      kwin_dbus_seen = 1
    }

    /^X-KDE-Wayland-Interfaces=/ {
      kwin_wayland_seen = 1
    }

    /^\[/ && $0 != "[Desktop Entry]" && !kwin_authorization_inserted {
      insert_kwin_authorization()
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
      if (!kwin_authorization_inserted) {
        insert_kwin_authorization()
      }
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
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
applications_dir="$data_home/applications"
service_menu_dirs=(
  "$data_home/kio/servicemenus"
  "$data_home/kservices5/ServiceMenus"
)
toolbelt_command=$(resolve_toolbelt_command "$data_home")
toolbelt_exec=$(desktop_exec_command "$toolbelt_command")

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
