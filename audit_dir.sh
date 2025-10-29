#!/usr/bin/env bash
# HomeSweetHome directory auditor (v4)
# Usage:
#   bash ./audit_dir.sh                # 기본(의존성/캐시 제외)
#   bash ./audit_dir.sh --full         # 전체 스캔
#   bash ./audit_dir.sh --depth 6      # tree 깊이 조절
#   bash ./audit_dir.sh --no-install   # tree/cloc 자동설치 건너뛰기

set -euo pipefail

# ---------------------------
# Options
# ---------------------------
TREE_DEPTH=6
FULL_SCAN=false
AUTO_INSTALL=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --depth) TREE_DEPTH="${2:-6}"; shift 2;;
    --full) FULL_SCAN=true; shift;;
    --no-install) AUTO_INSTALL=false; shift;;
    *) echo "Unknown option: $1"; exit 1;;
  esac
done

# ---------------------------
# Directories
# ---------------------------
AUDIT_DIR="./dir_audit"
mkdir -p "$AUDIT_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUT_FILE="${AUDIT_DIR}/${TIMESTAMP}_dir_audit.txt"

# ---------------------------
# Exclusions
# ---------------------------
EXCLUDES_DIRS=".git,.venv,venv,node_modules,dist,build,.idea,.vscode,__pycache__,.expo,.gradle,.next,.pytest_cache,.sass-cache,.cache"
EX_PAT='.git|.venv|venv|node_modules|dist|build|.idea|.vscode|__pycache__|.expo|.gradle|.next|.pytest_cache|.sass-cache|.cache'
FIND_EXCLUDE=(-not -path '*/.git/*' -not -path '*/.venv/*' -not -path '*/venv/*'
              -not -path '*/node_modules/*' -not -path '*/dist/*' -not -path '*/build/*'
              -not -path '*/.expo/*' -not -path '*/.gradle/*' -not -path '*/.next/*'
              -not -path '*/.pytest_cache/*' -not -path '*/__pycache__/*' -not -path '*/.sass-cache/*' -not -path '*/.cache/*')

if $FULL_SCAN; then
  EXCLUDES_DIRS=""
  EX_PAT=""
  FIND_EXCLUDE=()
fi

# ---------------------------
# Dependencies
# ---------------------------
need() { command -v "$1" >/dev/null 2>&1; }
if $AUTO_INSTALL; then
  if ! need tree; then echo "[i] installing tree"; sudo apt-get update && sudo apt-get install -y tree; fi
  if ! need cloc; then echo "[i] installing cloc"; sudo apt-get update && sudo apt-get install -y cloc; fi
fi

# ---------------------------
# Write audit
# ---------------------------
{
  echo "===== HomeSweetHome DIR AUDIT (v4) ====="
  date +"Generated at: %Y-%m-%d %H:%M:%S %Z"
  echo "Project root: $(pwd)"
  echo "Output file: $OUT_FILE"
  echo "Mode: $([ "$FULL_SCAN" = true ] && echo FULL || echo LEAN)"
  echo

  echo "== System =="
  uname -a || true
  echo

  echo "== Git =="
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Current branch: $(git rev-parse --abbrev-ref HEAD)"
    echo "Remote(s):"; git remote -v
    echo; echo "-- git status --"; git status --porcelain=v1
    echo; echo "-- recent commits --"; git log --oneline -n 10
  else
    echo "Not a git repo."
  fi
  echo

  echo "== Disk usage (top-level) =="
  du -h -d 1 2>/dev/null | sort -h
  echo

  echo "== Directory tree (depth <= $TREE_DEPTH, $([ "$FULL_SCAN" = true ] && echo 'no excludes' || echo "excludes: $EXCLUDES_DIRS")) =="
  if need tree; then
    if $FULL_SCAN; then
      tree -a -L "$TREE_DEPTH" .
    else
      tree -a -L "$TREE_DEPTH" -I "$EX_PAT" .
    fi
  else
    echo "(tree not installed; skipped)"
  fi
  echo

  echo "== Largest files (top 30) =="
  if $FULL_SCAN; then
    find . -type f -printf "%s\t%p\n" 2>/dev/null | sort -nr | head -n 30
  else
    find . -type f "${FIND_EXCLUDE[@]}" -printf "%s\t%p\n" 2>/dev/null | sort -nr | head -n 30
  fi
  echo

  echo "== Language breakdown (cloc) =="
  if need cloc; then
    if $FULL_SCAN || [[ -z "$EXCLUDES_DIRS" ]]; then
      cloc --quiet .
    else
      cloc --quiet --exclude-dir="$EXCLUDES_DIRS" .
    fi
  else
    echo "(cloc not installed; skipped)"
  fi
  echo

  echo "== Manifest files =="
  find . -name "package.json" -not -path "*/node_modules/*" -print
  find . -name "requirements*.txt" -print
  find . -name "pyproject.toml" -print
  echo

  echo "== Alembic directories =="
  find . -type d -name alembic -print
  echo

  echo "== Backend entry points =="
  find . -type f \( -name main.py -o -name app.py \) -print
  echo

  echo "== .env files (size only) =="
  while IFS= read -r f; do
    [ -f "$f" ] && echo "$(stat -c%s "$f") bytes  $f"
  done < <(find . -name ".env" -o -name ".env.*")
  echo

  echo "== Longest code/text files (top 20) =="
  find . -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' -o -name '*.py' -o -name '*.sql' -o -name '*.json' -o -name '*.md' \) \
    "${FIND_EXCLUDE[@]}" -printf "%p\n" \
  | xargs -I{} bash -c 'printf "%8s  %s\n" "$(wc -l < "{}" 2>/dev/null)" "{}"' \
  | sort -nr | head -n 20
  echo

} > "$OUT_FILE"

echo "✅ 생성 완료: $(realpath "$OUT_FILE")"
