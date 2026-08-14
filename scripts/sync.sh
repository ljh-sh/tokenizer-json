#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$REPO_ROOT/data"
SCRIPTS_DIR="$REPO_ROOT/scripts"
MIRROR="${HF_MIRROR:-https://hf-mirror.com}"
RELEASE_TAG="${RELEASE_TAG:-data}"

usage() {
  echo "Usage: $0 [--modelscope] <id> <huggingface-repo-or-url>"
  echo ""
  echo "Examples:"
  echo "  $0 qwen2_5 Qwen/Qwen2.5-7B-Instruct"
  echo "  $0 --modelscope qwen3 Qwen/Qwen3-0.6B"
  echo "  $0 --modelscope glm ZhipuAI/glm-4-9b-chat-hf"
  echo "  $0 llama3 NousResearch/Meta-Llama-3-8B"
  echo ""
  echo "Environment:"
  echo "  HF_MIRROR     default: https://hf-mirror.com"
  echo "  RELEASE_TAG   default: data"
  echo ""
  echo "Steps:"
  echo "  1. Download tokenizer.json"
  echo "  2. Validate JSON"
  echo "  3. Compress to <id>.tokenizer.json.xz"
  echo "  4. Regenerate index.tsv"
  echo "  5. Upload xz asset to GitHub release '$RELEASE_TAG'"
  exit 1
}

USE_MODELSCOPE=false

# Parse optional flags.
while [ $# -gt 0 ]; do
  case "$1" in
    --modelscope)
      USE_MODELSCOPE=true
      shift
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      ;;
    *)
      break
      ;;
  esac
done

if [ $# -lt 2 ]; then
  usage
fi

ID="$1"
SRC="$2"
JSON_OUT="$DATA_DIR/${ID}.tokenizer.json"
XZ_OUT="$DATA_DIR/${ID}.tokenizer.json.xz"
SRC_FILE="$DATA_DIR/${ID}.tokenizer.json.src"

# Normalize source to a full URL if it looks like "org/repo".
if [[ "$SRC" != http* ]]; then
  if [ "$USE_MODELSCOPE" = true ]; then
    SRC="https://modelscope.cn/api/v1/models/$SRC/repo?FilePath=tokenizer.json&Revision=master"
  else
    SRC="$MIRROR/$SRC/raw/main/tokenizer.json"
  fi
fi

mkdir -p "$DATA_DIR"

echo "[$ID] Downloading tokenizer.json from $SRC ..."
curl -L --fail --max-time 300 -o "$JSON_OUT" "$SRC"

SIZE_JSON="$(du -h "$JSON_OUT" | cut -f1)"
echo "[$ID] Saved raw tokenizer ($SIZE_JSON)"

# Validate JSON.
if ! python3 -m json.tool "$JSON_OUT" >/dev/null 2>&1; then
  echo "[$ID] ERROR: invalid JSON" >&2
  rm -f "$JSON_OUT"
  exit 1
fi

# Compress with xz.
echo "[$ID] Compressing to xz ..."
xz -k -f "$JSON_OUT"
SIZE_XZ="$(du -h "$XZ_OUT" | cut -f1)"
echo "[$ID] Compressed to $XZ_OUT ($SIZE_XZ)"

# Remove raw json from repo working tree (it is not tracked).
rm -f "$JSON_OUT"

# Write source note.
cat > "$SRC_FILE" <<EOF
id: $ID
url: $SRC
downloaded: $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

echo "[$ID] Wrote source note to $SRC_FILE"

# Regenerate index.tsv.
echo "[$ID] Regenerating index.tsv ..."
python3 "$SCRIPTS_DIR/generate-index.py"

# Upload to GitHub release.
echo "[$ID] Uploading $XZ_OUT to release '$RELEASE_TAG' ..."
if gh release view "$RELEASE_TAG" >/dev/null 2>&1; then
  gh release upload "$RELEASE_TAG" "$XZ_OUT" --clobber
else
  gh release create "$RELEASE_TAG" "$XZ_OUT" \
    --title "tokenizer-json data" \
    --notes "xz-compressed tokenizer.json release assets"
fi

echo "[$ID] Done."
