#!/usr/bin/env bash
# install.sh — Installer for wise-mode Claude Code skills and hooks
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/den-emon/wise-mode/main/install.sh | bash
#   wget -qO- https://raw.githubusercontent.com/den-emon/wise-mode/main/install.sh | bash
#
# The entire script is wrapped in main() so that a partial download
# never executes incomplete code.

main() {
    set -euo pipefail

    # ── Configuration ──────────────────────────────────────────────
    REPO_RAW_BASE="https://raw.githubusercontent.com/den-emon/wise-mode/main"

    # Skills to install: "name|file1,file2,..."
    SKILLS=(
        "terse-mode|SKILL.md"
        "swarm|SKILL.md"
        "wise|SKILL.md,CHECKLISTS.md,PATTERNS.md"
        "wise-cont|SKILL.md"
    )

    # Hook files to install
    HOOK_FILES=(
        "cclog-hook.sh"
        "sync_to_obsidian.py"
    )

    # Hooks configuration to merge into settings.local.json
    HOOKS_CONFIG='{
        "PostToolUse": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": ".claude/hooks/cclog-hook.sh PostToolUse",
                        "timeout": 5000
                    }
                ]
            }
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": ".claude/hooks/cclog-hook.sh Stop",
                        "timeout": 5000
                    }
                ]
            }
        ]
    }'

    # ── Colors (disabled when piped) ──────────────────────────────
    if [ -t 1 ]; then
        RED='\033[0;31m'
        GREEN='\033[0;32m'
        YELLOW='\033[0;33m'
        CYAN='\033[0;36m'
        BOLD='\033[1m'
        RESET='\033[0m'
    else
        RED='' GREEN='' YELLOW='' CYAN='' BOLD='' RESET=''
    fi

    info()  { printf "${CYAN}[info]${RESET}  %s\n" "$1"; }
    ok()    { printf "${GREEN}[ok]${RESET}    %s\n" "$1"; }
    warn()  { printf "${YELLOW}[warn]${RESET}  %s\n" "$1"; }
    error() { printf "${RED}[error]${RESET} %s\n" "$1" >&2; }

    # ── Preflight checks ─────────────────────────────────────────
    if command -v curl >/dev/null 2>&1; then
        fetch() { curl -fsSL --retry 3 --retry-delay 2 "$1"; }
    elif command -v wget >/dev/null 2>&1; then
        fetch() { wget -qO- --tries=3 "$1"; }
    else
        error "curl or wget is required but neither was found."
        exit 1
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        error "python3 is required for hooks configuration but was not found."
        exit 1
    fi

    # ── Detect project root ───────────────────────────────────────
    if [ -d ".git" ] || [ -d ".claude" ]; then
        PROJECT_ROOT="$(pwd)"
    else
        warn "No .git or .claude directory found in $(pwd)."
        printf "  Install here anyway? [y/N] "
        read -r answer </dev/tty
        case "$answer" in
            [yY]|[yY][eE][sS]) PROJECT_ROOT="$(pwd)" ;;
            *) error "Aborted. cd into your project root and retry."; exit 1 ;;
        esac
    fi

    # ── Check for existing installation ───────────────────────────
    EXISTING=0
    for skill_entry in "${SKILLS[@]}"; do
        skill_name="${skill_entry%%|*}"
        target=".claude/skills/${skill_name}"
        if [ -d "${PROJECT_ROOT}/${target}" ] && [ -f "${PROJECT_ROOT}/${target}/SKILL.md" ]; then
            EXISTING=1
            break
        fi
    done
    for hook_file in "${HOOK_FILES[@]}"; do
        if [ -f "${PROJECT_ROOT}/.claude/hooks/${hook_file}" ]; then
            EXISTING=1
            break
        fi
    done

    if [ "${EXISTING}" -eq 1 ]; then
        warn "One or more skills/hooks already exist in .claude/"
        printf "  Overwrite? [y/N] "
        read -r answer </dev/tty
        case "$answer" in
            [yY]|[yY][eE][sS]) : ;;
            *) info "Aborted. Existing installation unchanged."; exit 0 ;;
        esac
    fi

    # ── Download to temp dir first (atomic install) ───────────────
    TMPDIR_DOWNLOAD="$(mktemp -d)"
    trap 'rm -rf "${TMPDIR_DOWNLOAD}"' EXIT

    FAIL=0
    INSTALLED_FILES=()

    # Download skills
    for skill_entry in "${SKILLS[@]}"; do
        skill_name="${skill_entry%%|*}"
        skill_files_str="${skill_entry#*|}"
        IFS=',' read -ra skill_files <<< "${skill_files_str}"

        info "Downloading ${skill_name} skill files..."
        mkdir -p "${TMPDIR_DOWNLOAD}/skills/${skill_name}"

        for file in "${skill_files[@]}"; do
            url="${REPO_RAW_BASE}/skills/${skill_name}/${file}"
            dest="${TMPDIR_DOWNLOAD}/skills/${skill_name}/${file}"
            if fetch "${url}" > "${dest}" 2>/dev/null; then
                if [ ! -s "${dest}" ]; then
                    error "Downloaded ${skill_name}/${file} is empty."
                    FAIL=1
                fi
            else
                error "Failed to download ${skill_name}/${file} from ${url}"
                FAIL=1
            fi
        done

        # Verify SKILL.md has expected frontmatter
        if [ -f "${TMPDIR_DOWNLOAD}/skills/${skill_name}/SKILL.md" ]; then
            if ! head -1 "${TMPDIR_DOWNLOAD}/skills/${skill_name}/SKILL.md" | grep -q "^---"; then
                error "${skill_name}/SKILL.md does not look like a valid skill file (missing frontmatter)."
                FAIL=1
            fi
        fi
    done

    # Download hooks
    info "Downloading hook files..."
    mkdir -p "${TMPDIR_DOWNLOAD}/hooks"
    for hook_file in "${HOOK_FILES[@]}"; do
        url="${REPO_RAW_BASE}/hooks/${hook_file}"
        dest="${TMPDIR_DOWNLOAD}/hooks/${hook_file}"
        if fetch "${url}" > "${dest}" 2>/dev/null; then
            if [ ! -s "${dest}" ]; then
                error "Downloaded hooks/${hook_file} is empty."
                FAIL=1
            fi
        else
            error "Failed to download hooks/${hook_file} from ${url}"
            FAIL=1
        fi
    done

    if [ "${FAIL}" -ne 0 ]; then
        error "One or more files failed to download. Installation aborted."
        exit 1
    fi

    # ── Install skills ────────────────────────────────────────────
    for skill_entry in "${SKILLS[@]}"; do
        skill_name="${skill_entry%%|*}"
        skill_files_str="${skill_entry#*|}"
        IFS=',' read -ra skill_files <<< "${skill_files_str}"

        target_dir="${PROJECT_ROOT}/.claude/skills/${skill_name}"
        mkdir -p "${target_dir}"

        for file in "${skill_files[@]}"; do
            cp "${TMPDIR_DOWNLOAD}/skills/${skill_name}/${file}" "${target_dir}/${file}"
            INSTALLED_FILES+=("${target_dir}/${file}")
        done
    done

    # ── Install hooks ─────────────────────────────────────────────
    hooks_dir="${PROJECT_ROOT}/.claude/hooks"
    mkdir -p "${hooks_dir}"
    for hook_file in "${HOOK_FILES[@]}"; do
        cp "${TMPDIR_DOWNLOAD}/hooks/${hook_file}" "${hooks_dir}/${hook_file}"
        chmod +x "${hooks_dir}/${hook_file}"
        INSTALLED_FILES+=("${hooks_dir}/${hook_file}")
    done

    # ── Merge hooks config into settings.local.json ───────────────
    SETTINGS_PATH="${PROJECT_ROOT}/.claude/settings.local.json"
    python3 -c "
import json, os, sys

settings_path = sys.argv[1]
hooks_config = json.loads(sys.argv[2])

if os.path.exists(settings_path):
    with open(settings_path) as f:
        settings = json.load(f)
else:
    settings = {}

existing_hooks = settings.get('hooks', {})

for event, entries in hooks_config.items():
    if event not in existing_hooks:
        existing_hooks[event] = entries
    else:
        # Check if cclog hook already exists to avoid duplicates
        existing_cmds = set()
        for entry in existing_hooks[event]:
            for h in entry.get('hooks', []):
                existing_cmds.add(h.get('command', ''))
        for entry in entries:
            for h in entry.get('hooks', []):
                if h.get('command', '') not in existing_cmds:
                    existing_hooks[event].append(entry)
                    break

settings['hooks'] = existing_hooks

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')
" "${SETTINGS_PATH}" "${HOOKS_CONFIG}"

    ok "Hooks configuration merged into .claude/settings.local.json"

    # Remove legacy skills if present
    LEGACY_CAVEMAN="${PROJECT_ROOT}/.claude/skills/caveman"
    if [ -d "${LEGACY_CAVEMAN}" ]; then
        rm -rf "${LEGACY_CAVEMAN}"
        info "Removed legacy caveman skill (replaced by terse-mode)"
    fi

    LEGACY_CCLOG="${PROJECT_ROOT}/.claude/skills/cclog"
    if [ -d "${LEGACY_CCLOG}" ]; then
        rm -rf "${LEGACY_CCLOG}"
        info "Removed legacy cclog skill (replaced by hook)"
    fi

    # ── Summary ───────────────────────────────────────────────────
    echo ""
    printf "${BOLD}${GREEN}  wise-mode installed successfully!${RESET}\n"
    echo ""
    info "Installed files:"
    for f in "${INSTALLED_FILES[@]}"; do
        echo "    ${f}"
    done
    echo ""
    info "Usage:"
    echo "    /terse-mode - Brevity mode with lite/full/ultra intensity"
    echo "    /swarm      - Parallel delegation planning"
    echo "    /wise       - Architect mode for a single task"
    echo "    /wise-cont  - Architect mode for the entire session"
    echo "    cclog       - Auto-records sessions via hooks (no commands needed)"
    echo ""
    info "Session logs are saved to .claude/log/ automatically."
    echo ""

    # ── Hint: .gitignore ──────────────────────────────────────────
    if [ -f ".gitignore" ]; then
        if ! grep -q "\.claude/" ".gitignore" 2>/dev/null; then
            warn "Consider adding .claude/ to .gitignore if you don't want to track skill files."
        fi
    fi
}

# Run everything inside main() to guard against partial downloads
main "$@"
