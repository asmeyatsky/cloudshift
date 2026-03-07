#!/usr/bin/env bash
# Export Ollama model for air-gapped deployment.
#
# Usage:
#   ./scripts/export-model.sh                    # exports default model
#   ./scripts/export-model.sh qwen2.5-coder:7b   # exports specific model
#
# Output: cloudshift-ollama-bundle.tar.gz in current directory

set -euo pipefail

MODEL="${1:-qwen2.5-coder:14b}"
OUTPUT="cloudshift-ollama-bundle.tar.gz"
OLLAMA_DIR="${OLLAMA_MODELS:-$HOME/.ollama/models}"

echo "=== CloudShift Model Export ==="
echo "Model:  $MODEL"
echo "Source: $OLLAMA_DIR"
echo ""

# Verify model exists
if ! ollama list | grep -q "${MODEL}"; then
    echo "ERROR: Model '$MODEL' not found. Pull it first:"
    echo "  ollama pull $MODEL"
    exit 1
fi

# Check disk space (need ~model size for the archive)
MODEL_SIZE=$(du -sm "$OLLAMA_DIR" 2>/dev/null | cut -f1)
FREE_SPACE=$(df -m . | tail -1 | awk '{print $4}')
echo "Model directory size: ${MODEL_SIZE:-unknown} MB"
echo "Free disk space:      ${FREE_SPACE} MB"
echo ""

if [[ -n "$MODEL_SIZE" && "$FREE_SPACE" -lt "$MODEL_SIZE" ]]; then
    echo "WARNING: May not have enough free space for the archive."
    echo "         Need ~${MODEL_SIZE} MB, have ${FREE_SPACE} MB."
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

echo "Creating archive..."
tar -czf "$OUTPUT" -C "$(dirname "$OLLAMA_DIR")" "$(basename "$OLLAMA_DIR")"

ARCHIVE_SIZE=$(du -h "$OUTPUT" | cut -f1)
echo ""
echo "=== Export complete ==="
echo "Archive: $OUTPUT ($ARCHIVE_SIZE)"
echo ""
echo "To import on air-gapped machine:"
echo "  1. Transfer $OUTPUT to target machine"
echo "  2. Install Ollama: brew install ollama (macOS) or curl -fsSL https://ollama.ai/install.sh | sh (Linux)"
echo "  3. Extract: tar -xzf $OUTPUT -C ~/.ollama/"
echo "  4. Start:   ollama serve"
echo "  5. Verify:  ollama list"
