#!/usr/bin/env bash

if [ -z "${BASH_VERSION:-}" ]; then
	if command -v bash >/dev/null 2>&1; then
		exec bash "$0" "$@"
	fi
	echo "Error: this script requires bash" >&2
	exit 1
fi

set -euo pipefail

usage() {
	echo "Usage: $0 <email> [--skip-session]" >&2
	echo "Optional env: SESSION_COLLECTOR_INSTALL_SCRIPT_URL, SESSION_COLLECTOR_VERSION, SESSION_WINDOW_MINUTES" >&2
}

SKIP_SESSION=false
POSITIONAL=()

for arg in "$@"; do
	case "$arg" in
	--skip-session)
		SKIP_SESSION=true
		;;
	-h|--help)
		usage
		exit 0
		;;
	--*)
		echo "Error: Unknown option: $arg" >&2
		usage
		exit 1
		;;
	*)
		POSITIONAL+=("$arg")
		;;
	esac
done

if [ "${#POSITIONAL[@]}" -gt 1 ]; then
	echo "Error: Too many arguments" >&2
	usage
	exit 1
fi

EMAIL="${POSITIONAL[0]:-${EMAIL:-}}"

if [ -z "$EMAIL" ]; then
	echo "Error: EMAIL must be provided as an argument or set as an environment variable" >&2
	usage
	exit 1
fi

require_cmd() {
	if ! command -v "$1" >/dev/null 2>&1; then
		echo "Error: Required command not found: $1" >&2
		exit 1
	fi
}

require_cmd zip
require_cmd curl

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TEMP_DIR=$(mktemp -d)
ZIP_FILE="$TEMP_DIR/submission.zip"
AGENT_SESSIONS_DIR="$PROJECT_ROOT/agent-sessions"
WINDOW_MINUTES="${SESSION_WINDOW_MINUTES:-90}"
COLLECTOR_CACHE_DIR="${SESSION_COLLECTOR_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/composio-session-collector}"
DEFAULT_INSTALLER_URL="https://eng.hiring.composio.io/api/agent-sessions/install"
COLLECTOR_SOURCE=""
COLLECTOR_BIN=""

trap 'rm -rf "$TEMP_DIR"' EXIT

collector_platform() {
	local os_name
	local arch_name

	os_name=$(uname -s | tr '[:upper:]' '[:lower:]')
	arch_name=$(uname -m)

	case "$arch_name" in
	x86_64 | amd64)
		arch_name="x64"
		;;
	arm64 | aarch64)
		arch_name="arm64"
		;;
	esac

	echo "${os_name}-${arch_name}"
}

run_collector() {
	if [ -n "$COLLECTOR_BIN" ]; then
		"$COLLECTOR_BIN" "$@"
		return
	fi

	if [ -n "$COLLECTOR_SOURCE" ]; then
		bun "$COLLECTOR_SOURCE" "$@"
		return
	fi

	echo "Error: collector command not resolved" >&2
	exit 1
}

set_collector_bin_if_valid() {
	local candidate="$1"
	if [ -x "$candidate" ] && "$candidate" --help >/dev/null 2>&1; then
		COLLECTOR_BIN="$candidate"
		return 0
	fi
	return 1
}

install_collector_with_script() {
	local installer_script="$1"
	local version
	local installed_path=""

	version="${SESSION_COLLECTOR_VERSION:-latest}"

	if [ ! -f "$installer_script" ]; then
		return 1
	fi

	if [ ! -x "$installer_script" ]; then
		chmod +x "$installer_script"
	fi

	echo "Installing session collector via $installer_script ($version)..."
	if installed_path=$(
		SESSION_COLLECTOR_INSTALL_DIR="$COLLECTOR_CACHE_DIR" \
		SESSION_COLLECTOR_RELEASE_BASE_URL="${SESSION_COLLECTOR_RELEASE_BASE_URL:-}" \
		SESSION_COLLECTOR_CUSTOM_ID_PREFIX="${SESSION_COLLECTOR_CUSTOM_ID_PREFIX:-}" \
		SESSION_COLLECTOR_BIN_NAME="collect-agent-sessions" \
		"$installer_script" "$version"
	); then
		if [ -n "$installed_path" ] && set_collector_bin_if_valid "$installed_path"; then
			return 0
		fi
	fi

	if set_collector_bin_if_valid "$COLLECTOR_CACHE_DIR/collect-agent-sessions"; then
		return 0
	fi

	return 1
}

try_install_with_local_script() {
	local candidate
	for candidate in \
		"$PROJECT_ROOT/../internal/tools/install-session-collector.sh"; do
		if install_collector_with_script "$candidate"; then
			return 0
		fi
	done
	return 1
}

try_install_with_remote_script() {
	local installer_url
	local tmp_script

	installer_url="${SESSION_COLLECTOR_INSTALL_SCRIPT_URL:-$DEFAULT_INSTALLER_URL}"
	if [ -z "$installer_url" ]; then
		return 1
	fi

	tmp_script="$TEMP_DIR/install-session-collector.sh"
	echo "Downloading session collector installer..."
	if ! curl -fsSL "$installer_url" -o "$tmp_script"; then
		return 1
	fi

	install_collector_with_script "$tmp_script"
}

resolve_collector() {
	local platform
	local source_candidate
	local local_compiled_bin

	platform="$(collector_platform)"

	if try_install_with_remote_script; then
		return
	fi

	if try_install_with_local_script; then
		return
	fi

	source_candidate="$PROJECT_ROOT/../internal/tools/agent-session.ts"
	if [ -f "$source_candidate" ] && command -v bun >/dev/null 2>&1; then
		mkdir -p "$COLLECTOR_CACHE_DIR"
		local_compiled_bin="$COLLECTOR_CACHE_DIR/collect-agent-sessions-${platform}-local"
		if [ -x "$local_compiled_bin" ] && [ "$source_candidate" -ot "$local_compiled_bin" ]; then
			COLLECTOR_BIN="$local_compiled_bin"
			return
		fi

		echo "Compiling local collector binary with Bun..."
		if bun build --compile --outfile "$local_compiled_bin" "$source_candidate" >/dev/null 2>&1; then
			chmod +x "$local_compiled_bin"
			COLLECTOR_BIN="$local_compiled_bin"
			return
		fi

		COLLECTOR_SOURCE="$source_candidate"
		return
	fi

	echo "Error: unable to resolve agent session collector" >&2
	echo "Set SESSION_COLLECTOR_INSTALL_SCRIPT_URL to a valid installer endpoint." >&2
	exit 1
}

write_skip_manifest() {
	run_collector \
		--write-skip-manifest \
		--project-root "$PROJECT_ROOT" \
		--output-dir "$AGENT_SESSIONS_DIR" \
		--window-minutes "$WINDOW_MINUTES"
}

approve_empty_manifest() {
	run_collector \
		--approve-empty-manifest \
		--manifest-file "$AGENT_SESSIONS_DIR/manifest.json"
}

read_total_artifacts() {
	run_collector \
		--read-total-artifacts \
		--manifest-file "$AGENT_SESSIONS_DIR/manifest.json"
}

collect_sessions() {
	if [ "$SKIP_SESSION" = true ]; then
		echo "Skipping agent session tracing (--skip-session)."
		rm -rf "$AGENT_SESSIONS_DIR"
		mkdir -p "$AGENT_SESSIONS_DIR"
		write_skip_manifest
		return
	fi

	echo "Collecting agent sessions (last ${WINDOW_MINUTES} minutes)..."
	run_collector \
		--project-root "$PROJECT_ROOT" \
		--output-dir "$AGENT_SESSIONS_DIR" \
		--window-minutes "$WINDOW_MINUTES"

	MANIFEST_FILE="$AGENT_SESSIONS_DIR/manifest.json"
	if [ ! -f "$MANIFEST_FILE" ]; then
		echo "Error: collector did not produce $MANIFEST_FILE" >&2
		exit 1
	fi

	TOTAL_ARTIFACTS="$(read_total_artifacts)"
	if [ "$TOTAL_ARTIFACTS" -eq 0 ]; then
		if [ -t 0 ] && [ -t 1 ]; then
			echo "No recent agent sessions found in the last ${WINDOW_MINUTES} minutes for this folder."
			read -r -p "Continue upload without session tracing? [y/N] " CONTINUE_UPLOAD
			case "$CONTINUE_UPLOAD" in
			[yY]|[yY][eE][sS])
				approve_empty_manifest
				;;
			*)
				echo "Upload cancelled. Re-run with --skip-session to bypass session tracing." >&2
				exit 1
				;;
			esac
		else
			echo "Error: no recent agent sessions found in the last ${WINDOW_MINUTES} minutes." >&2
			echo "Re-run with --skip-session to bypass session tracing in non-interactive mode." >&2
			exit 1
		fi
	fi
}

resolve_collector
collect_sessions

echo "Creating zip file..."

cd "$PROJECT_ROOT"

zip -r "$ZIP_FILE" . \
	-x ".git/*" \
	-x "node_modules/*" \
	-x ".session-collector-bin/*" \
	-x ".venv/*" \
	-x "__pycache__/*" \
	-x ".cache/*" \
	-x ".next/*" \
	-x "*.tsbuildinfo" \
	-x "dist/*" \
	-x ".DS_Store" \
	-x ".env*" \
	-x "*.log" \
	-x "coverage/*" \
	-x "*.pem" \
	-x "project.zip"

if [ ! -f "$ZIP_FILE" ]; then
	echo "Error: Failed to create zip file" >&2
	exit 1
fi

echo "Uploading submission..."

SUBMIT_URL="${SUBMIT_URL:-https://eng.hiring.composio.io/api/submit}"

if ! RESPONSE=$(curl -sS -w "\n%{http_code}" -X POST "$SUBMIT_URL" \
	-F "email=$EMAIL" \
	-F "task=dep" \
	-F "file=@$ZIP_FILE"); then
	echo "Error: Upload request failed before receiving a response" >&2
	exit 1
fi

HTTP_CODE=$(printf '%s\n' "$RESPONSE" | tail -n1)
BODY=$(printf '%s\n' "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
	echo "Submission successful!"
	if command -v jq >/dev/null 2>&1; then
		echo "$BODY" | jq .
	else
		echo "$BODY"
	fi
else
	echo "Error: Submission failed (HTTP $HTTP_CODE)" >&2
	echo "$BODY" >&2
	exit 1
fi
